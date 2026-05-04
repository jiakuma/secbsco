from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.stat_template import StatTemplate
from app.schemas.stat_template_schema import (
    StatTemplateCreate,
    StatTemplateUpdate,
)


class StatTemplateService:

    @staticmethod
    def list_templates(
        db: Session,
        keyword: Optional[str] = None,
        stat_type: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ):
        query = db.query(StatTemplate)

        if keyword:
            query = query.filter(
                or_(
                    StatTemplate.template_code.like(f"%{keyword}%"),
                    StatTemplate.template_name.like(f"%{keyword}%")
                )
            )

        if stat_type:
            query = query.filter(StatTemplate.stat_type == stat_type)

        if status:
            query = query.filter(StatTemplate.status == status)

        total = query.count()

        items = (
            query
            .order_by(StatTemplate.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items

    @staticmethod
    def get_template_by_id(
        db: Session,
        template_id: int
    ) -> Optional[StatTemplate]:
        return (
            db.query(StatTemplate)
            .filter(StatTemplate.id == template_id)
            .first()
        )

    @staticmethod
    def get_template_by_code(
        db: Session,
        template_code: str
    ) -> Optional[StatTemplate]:
        return (
            db.query(StatTemplate)
            .filter(StatTemplate.template_code == template_code)
            .first()
        )

    @staticmethod
    def create_template(
        db: Session,
        template_req: StatTemplateCreate
    ) -> StatTemplate:
        template = StatTemplate(
            template_code=template_req.template_code,
            template_name=template_req.template_name,
            stat_type=template_req.stat_type,
            metrics_json=template_req.metrics_json,
            params_schema_json=template_req.params_schema_json,
            status=template_req.status or "enabled",
            description=template_req.description,
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        return template

    @staticmethod
    def update_template(
        db: Session,
        template: StatTemplate,
        template_req: StatTemplateUpdate
    ) -> StatTemplate:
        update_data = template_req.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(template, key, value)

        db.commit()
        db.refresh(template)

        return template

    @staticmethod
    def update_template_status(
        db: Session,
        template: StatTemplate,
        status: str
    ) -> StatTemplate:
        template.status = status

        db.commit()
        db.refresh(template)

        return template

    @staticmethod
    def build_template_info(template: StatTemplate) -> dict:
        return {
            "id": template.id,
            "template_code": template.template_code,
            "template_name": template.template_name,
            "stat_type": template.stat_type,
            "metrics_json": template.metrics_json,
            "params_schema_json": template.params_schema_json,
            "status": template.status,
            "description": template.description,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }