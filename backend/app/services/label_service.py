from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID

from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.lib.pagesizes import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import DomainError, NotFoundError
from app.models.enums import AliasType, AuditEventType, IdentifierType
from app.models.label import LabelPrintEvent, SampleLabel
from app.models.sample import Sample
from app.services.audit_service import audit_service
from app.services.sample_service import sample_service
from app.storage.local import storage


class LabelService:
    def generate(self, db: Session, sample_uuid: UUID, actor_id: UUID) -> SampleLabel:
        sample = sample_service.get_by_uuid(db, sample_uuid)
        barcode_value = next((a.value for a in sample.aliases if a.alias_type == AliasType.BARCODE), sample.sample_id)
        png_bytes, pdf_bytes = self._render(sample, barcode_value)
        label_code = f"LBL-{sample.sample_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        png_key = f"labels/{sample.sample_id}/{label_code}.png"
        pdf_key = f"labels/{sample.sample_id}/{label_code}.pdf"
        storage.save(png_key, png_bytes)
        storage.save(pdf_key, pdf_bytes)
        label = SampleLabel(
            sample_id=sample.id,
            label_code=label_code,
            barcode_format="code128",
            png_storage_key=png_key,
            pdf_storage_key=pdf_key,
            print_count=1,
            created_by=actor_id,
        )
        db.add(label)
        db.flush()
        db.add(
            LabelPrintEvent(
                label_id=label.id,
                sample_id=sample.id,
                reason="Initial print",
                sequence_number=1,
                is_reprint=False,
                created_by=actor_id,
            )
        )
        audit_service.record(
            db,
            event_type=AuditEventType.LABEL_CREATED,
            entity_type="SampleLabel",
            entity_id=label.id,
            actor_user_id=actor_id,
            after_state={"label_code": label_code, "sample_id": sample.sample_id},
        )
        db.commit()
        db.refresh(label)
        return label

    def reprint(self, db: Session, label_id: UUID, actor_id: UUID, reason: str) -> SampleLabel:
        if not reason or not reason.strip():
            raise DomainError("REPRINT_REASON_REQUIRED", "A reprint reason is required.")
        label = db.scalar(
            select(SampleLabel).options(selectinload(SampleLabel.print_events)).where(SampleLabel.id == label_id)
        )
        if label is None:
            raise NotFoundError("LABEL_NOT_FOUND", "Label not found")
        label.print_count += 1
        db.add(
            LabelPrintEvent(
                label_id=label.id,
                sample_id=label.sample_id,
                reason=reason.strip(),
                sequence_number=label.print_count,
                is_reprint=True,
                created_by=actor_id,
            )
        )
        audit_service.record(
            db,
            event_type=AuditEventType.LABEL_REPRINTED,
            entity_type="SampleLabel",
            entity_id=label.id,
            actor_user_id=actor_id,
            reason=reason.strip(),
            after_state={"print_count": label.print_count},
        )
        db.commit()
        db.refresh(label)
        return label

    def _render(self, sample: Sample, barcode_value: str) -> tuple[bytes, bytes]:
        rv = Code128(barcode_value, writer=ImageWriter())
        png_buffer = BytesIO()
        rv.write(
            png_buffer,
            options={"write_text": True, "module_height": 12.0, "font_size": 8, "text_distance": 3, "quiet_zone": 2},
        )
        png_bytes = png_buffer.getvalue()

        pdf_buffer = BytesIO()
        width, height = 80 * mm, 40 * mm
        c = canvas.Canvas(pdf_buffer, pagesize=(width, height))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(4 * mm, 34 * mm, sample.sample_id)
        c.setFont("Helvetica", 7)
        c.drawString(4 * mm, 30 * mm, f"Type: {sample.sample_type}")
        c.drawString(4 * mm, 26 * mm, f"Qty: {sample.quantity_remaining} {sample.quantity_unit}")
        c.drawString(4 * mm, 22 * mm, f"Barcode: {barcode_value}")
        img = ImageReader(BytesIO(png_bytes))
        c.drawImage(img, 4 * mm, 4 * mm, width=72 * mm, height=16 * mm, preserveAspectRatio=True, mask="auto")
        c.showPage()
        c.save()
        return png_bytes, pdf_buffer.getvalue()


label_service = LabelService()
