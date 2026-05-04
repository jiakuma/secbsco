from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.node import Node
from app.models.agency import Agency
from app.schemas.node_schema import NodeCreate, NodeUpdate


class NodeService:

    @staticmethod
    def list_nodes(
        db: Session,
        keyword: Optional[str] = None,
        agency_id: Optional[int] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ):
        query = db.query(Node)

        if keyword:
            query = query.filter(
                or_(
                    Node.node_code.like(f"%{keyword}%"),
                    Node.node_name.like(f"%{keyword}%")
                )
            )

        if agency_id:
            query = query.filter(Node.agency_id == agency_id)

        if status:
            query = query.filter(Node.status == status)

        total = query.count()

        items = (
            query
            .order_by(Node.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items

    @staticmethod
    def get_node_by_id(db: Session, node_id: int) -> Optional[Node]:
        return db.query(Node).filter(Node.id == node_id).first()

    @staticmethod
    def get_node_by_code(db: Session, node_code: str) -> Optional[Node]:
        return db.query(Node).filter(Node.node_code == node_code).first()

    @staticmethod
    def get_agency_by_id(db: Session, agency_id: int) -> Optional[Agency]:
        return db.query(Agency).filter(Agency.id == agency_id).first()

    @staticmethod
    def create_node(db: Session, node_req: NodeCreate) -> Node:
        node = Node(
            agency_id=node_req.agency_id,
            node_code=node_req.node_code,
            node_name=node_req.node_name,
            node_type=node_req.node_type,
            endpoint=node_req.endpoint,
            status=node_req.status or "offline",
            description=node_req.description,
        )

        db.add(node)
        db.commit()
        db.refresh(node)

        return node

    @staticmethod
    def update_node(
        db: Session,
        node: Node,
        node_req: NodeUpdate
    ) -> Node:
        update_data = node_req.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(node, key, value)

        db.commit()
        db.refresh(node)

        return node

    @staticmethod
    def update_node_status(
        db: Session,
        node: Node,
        status: str
    ) -> Node:
        node.status = status

        db.commit()
        db.refresh(node)

        return node

    @staticmethod
    def build_node_info(node: Node) -> dict:
        return {
            "id": node.id,
            "agency_id": node.agency_id,
            "node_code": node.node_code,
            "node_name": node.node_name,
            "node_type": node.node_type,
            "endpoint": node.endpoint,
            "status": node.status,
            "last_heartbeat_at": node.last_heartbeat_at,
            "description": node.description,
            "created_at": node.created_at,
            "updated_at": node.updated_at,
        }