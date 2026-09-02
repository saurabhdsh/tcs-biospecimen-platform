from collections import defaultdict, deque
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import DomainError
from app.models.enums import (
    AuditEventType,
    IdentifierType,
    LineageRelationshipType,
    QuantityTransactionType,
    SampleStatus,
)
from app.models.lineage import LineageRelationship, QuantityTransaction
from app.models.sample import Sample
from app.services.audit_service import audit_service
from app.services.quantity_service import assert_positive, convert, parse_unit
from app.services.sample_service import sample_service
from app.services.state_machine import lock_sample, state_machine


class LineageService:
    def _load_edges(self, db: Session) -> list[tuple[UUID, UUID]]:
        rows = db.execute(
            select(LineageRelationship.parent_sample_id, LineageRelationship.child_sample_id)
        ).all()
        return [(r.parent_sample_id, r.child_sample_id) for r in rows]

    def _descendants(self, edges: list[tuple[UUID, UUID]], start: UUID) -> set[UUID]:
        graph: dict[UUID, list[UUID]] = defaultdict(list)
        for parent, child in edges:
            graph[parent].append(child)
        seen: set[UUID] = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for nxt in graph.get(node, []):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def _would_cycle(self, db: Session, parent_id: UUID, child_id: UUID) -> bool:
        if parent_id == child_id:
            return True
        edges = self._load_edges(db)
        # If proposed child can already reach proposed parent, adding parent->child creates a cycle.
        reachable = self._descendants(edges, child_id)
        return parent_id in reachable

    def create_child(
        self,
        db: Session,
        *,
        parent_id: UUID,
        actor_id: UUID,
        relationship_type: str,
        output_quantity: Decimal,
        output_unit: str,
        parent_quantity_consumed: Decimal,
        child_sample_type: str,
        existing_child_id: UUID | None = None,
    ) -> Sample:
        try:
            rel_type = LineageRelationshipType(relationship_type)
        except ValueError as exc:
            raise DomainError("INVALID_RELATIONSHIP_TYPE", "relationship_type must be ALIQUOT or DERIVATIVE.") from exc

        assert_positive(output_quantity, "output_quantity")
        assert_positive(parent_quantity_consumed, "parent_quantity_consumed")

        parent = lock_sample(db, parent_id)
        parse_unit(output_unit)
        parse_unit(parent.quantity_unit)
        try:
            consumed_in_parent_unit = convert(parent_quantity_consumed, output_unit, parent.quantity_unit)
        except DomainError:
            consumed_in_parent_unit = convert(parent_quantity_consumed, parent.quantity_unit, parent.quantity_unit)

        if consumed_in_parent_unit > parent.quantity_remaining:
            raise DomainError(
                "INSUFFICIENT_QUANTITY",
                "Consumed quantity exceeds remaining parent quantity.",
                details={
                    "remaining": str(parent.quantity_remaining),
                    "consumed": str(consumed_in_parent_unit),
                    "unit": parent.quantity_unit,
                },
            )

        child: Sample
        if existing_child_id:
            if self._would_cycle(db, parent.id, existing_child_id):
                audit_service.record(
                    db,
                    event_type=AuditEventType.LINEAGE_CYCLE_REJECTED,
                    entity_type="Sample",
                    entity_id=parent.id,
                    actor_user_id=actor_id,
                    reason="Circular lineage rejected",
                    metadata={"parent_id": str(parent.id), "child_id": str(existing_child_id)},
                )
                db.commit()
                raise DomainError(
                    "LINEAGE_CYCLE",
                    "This relationship would create a circular lineage.",
                    details={"parent_id": str(parent.id), "child_id": str(existing_child_id)},
                )
            child = lock_sample(db, existing_child_id)
        else:
            child = sample_service.create_sample(
                db,
                actor_id=actor_id,
                sample_type=child_sample_type,
                quantity=output_quantity,
                quantity_unit=output_unit,
                material_type=parent.material_type,
                source_location=parent.source_location,
                temperature_requirement=parent.temperature_requirement,
                shipment_id=parent.shipment_id,
                status=SampleStatus.RECEIVED,
            )

        before_qty = parent.quantity_remaining
        parent.quantity_remaining = parent.quantity_remaining - consumed_in_parent_unit
        rel = LineageRelationship(
            parent_sample_id=parent.id,
            child_sample_id=child.id,
            relationship_type=rel_type.value,
            parent_quantity_consumed=consumed_in_parent_unit,
            child_quantity_produced=output_quantity,
            quantity_unit=parent.quantity_unit,
            created_by=actor_id,
        )
        db.add(rel)
        db.flush()
        db.add(
            QuantityTransaction(
                sample_id=parent.id,
                related_sample_id=child.id,
                lineage_relationship_id=rel.id,
                transaction_type=QuantityTransactionType.CONSUME.value,
                quantity=consumed_in_parent_unit,
                quantity_unit=parent.quantity_unit,
                quantity_before=before_qty,
                quantity_after=parent.quantity_remaining,
                created_by=actor_id,
            )
        )
        db.add(
            QuantityTransaction(
                sample_id=child.id,
                related_sample_id=parent.id,
                lineage_relationship_id=rel.id,
                transaction_type=QuantityTransactionType.PRODUCE.value,
                quantity=output_quantity,
                quantity_unit=output_unit,
                quantity_before=Decimal("0"),
                quantity_after=child.quantity_remaining,
                created_by=actor_id,
            )
        )
        event_type = (
            AuditEventType.ALIQUOT_CREATED
            if rel_type == LineageRelationshipType.ALIQUOT
            else AuditEventType.DERIVATIVE_CREATED
        )
        audit_service.record(
            db,
            event_type=event_type,
            entity_type="Sample",
            entity_id=child.id,
            actor_user_id=actor_id,
            after_state={"parent": parent.sample_id, "child": child.sample_id, "type": rel_type.value},
        )
        audit_service.record(
            db,
            event_type=AuditEventType.LINEAGE_CREATED,
            entity_type="LineageRelationship",
            entity_id=rel.id,
            actor_user_id=actor_id,
            after_state={
                "parent_sample_id": parent.sample_id,
                "child_sample_id": child.sample_id,
                "relationship_type": rel_type.value,
            },
        )
        audit_service.record(
            db,
            event_type=AuditEventType.QUANTITY_CHANGED,
            entity_type="Sample",
            entity_id=parent.id,
            actor_user_id=actor_id,
            before_state={"quantity_remaining": str(before_qty)},
            after_state={"quantity_remaining": str(parent.quantity_remaining)},
        )
        db.commit()
        return sample_service.get_by_uuid(db, child.id)

    def graph(self, db: Session, sample_uuid: UUID) -> dict:
        sample = sample_service.get_by_uuid(db, sample_uuid)
        edges = self._load_edges(db)
        reverse = [(c, p) for p, c in edges]
        forward_ids = self._descendants(edges, sample.id)
        backward_ids = self._descendants(reverse, sample.id)
        node_ids = {sample.id} | forward_ids | backward_ids
        samples = list(
            db.scalars(
                select(Sample)
                .options(selectinload(Sample.identifiers), selectinload(Sample.aliases))
                .where(Sample.id.in_(node_ids))
            )
        )
        rels = list(
            db.scalars(
                select(LineageRelationship).where(
                    LineageRelationship.parent_sample_id.in_(node_ids),
                    LineageRelationship.child_sample_id.in_(node_ids),
                )
            )
        )
        nodes = []
        for s in samples:
            nodes.append(
                {
                    "id": str(s.id),
                    "sample_id": s.sample_id,
                    "sample_type": s.sample_type,
                    "quantity": str(s.quantity_remaining),
                    "unit": s.quantity_unit,
                    "status": s.status,
                    "is_center": s.id == sample.id,
                }
            )
        edge_payload = [
            {
                "id": str(r.id),
                "source": str(r.parent_sample_id),
                "target": str(r.child_sample_id),
                "relationship_type": r.relationship_type,
                "consumed": str(r.parent_quantity_consumed),
                "produced": str(r.child_quantity_produced),
                "unit": r.quantity_unit,
            }
            for r in rels
        ]
        return {"center_sample_id": sample.sample_id, "nodes": nodes, "edges": edge_payload}


lineage_service = LineageService()
