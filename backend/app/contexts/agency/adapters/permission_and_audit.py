from ..domain.ports import AgencyPermissionPort, AgencyAuditPort


class AccessControlPermissionAdapter(AgencyPermissionPort):
    def __init__(self, db):
        self._db = db

    def get_manageable_agency_ids(self, current_user):
        from app.contexts.shared.resource_permission_service import get_manageable_agency_ids
        return get_manageable_agency_ids(self._db, current_user)

    def check_can_create_child_agency(self, current_user, parent_agency_id, agency_level):
        from app.contexts.shared.resource_permission_service import check_can_create_child_agency
        check_can_create_child_agency(self._db, current_user, parent_agency_id, agency_level)

    def check_can_manage_agency(self, current_user, agency_id):
        from app.contexts.shared.resource_permission_service import check_can_manage_agency
        check_can_manage_agency(self._db, current_user, agency_id)


class ResourceChainAuditAdapter(AgencyAuditPort):
    def __init__(self, db):
        self._db = db

    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type, resource_id, agency_id, request=None):
        from app.contexts.shared.access_control_service import write_operate_log
        write_operate_log(db=db, user_id=user_id, username=username, operation_type=operation_type,
                          resource_type=resource_type, resource_id=resource_id, agency_id=agency_id, request=request)

    def anchor_resource_operation(self, db, *, resource_type, resource_id, operation_type, operator, agency_id=None, before_data=None, after_data=None):
        from app.contexts.shared.resource_chain_service import anchor_resource_operation
        return anchor_resource_operation(db, resource_type=resource_type, resource_id=resource_id,
                                        operation_type=operation_type, operator=operator,
                                        agency_id=agency_id, before_data=before_data, after_data=after_data)
