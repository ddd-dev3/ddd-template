from typing import Optional, Any
from abc import ABC


class DomainException(Exception, ABC):
    """
    领域异常基类
    
    所有领域层异常都应该继承此类。
    领域异常表示业务规则违反或领域逻辑错误。
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        super().__init__(self.message)


class EntityNotFoundException(DomainException):
    """实体未找到异常"""
    
    def __init__(self, entity_type: str, entity_id: Any):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            code="ENTITY_NOT_FOUND"
        )


class AggregateNotFoundException(DomainException):
    """聚合根未找到异常"""
    
    def __init__(self, aggregate_type: str, aggregate_id: Any):
        self.aggregate_type = aggregate_type
        self.aggregate_id = aggregate_id
        super().__init__(
            message=f"{aggregate_type} aggregate with id '{aggregate_id}' not found",
            code="AGGREGATE_NOT_FOUND"
        )


class BusinessRuleViolationException(DomainException):
    """业务规则违反异常"""
    
    def __init__(self, rule: str, message: str):
        self.rule = rule
        super().__init__(
            message=f"Business rule '{rule}' violated: {message}",
            code="BUSINESS_RULE_VIOLATION"
        )


class InvariantViolationException(DomainException):
    """不变量违反异常"""
    
    def __init__(self, invariant: str, message: str):
        self.invariant = invariant
        super().__init__(
            message=f"Invariant '{invariant}' violated: {message}",
            code="INVARIANT_VIOLATION"
        )


class DomainValidationException(DomainException):
    """领域验证异常"""
    
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        super().__init__(
            message=f"Validation failed for {field}: {message}",
            code="DOMAIN_VALIDATION_ERROR"
        )


class InvalidValueObjectException(DomainException):
    """无效值对象异常"""
    
    def __init__(self, value_object_type: str, value: Any, reason: str):
        self.value_object_type = value_object_type
        self.value = value
        super().__init__(
            message=f"Invalid {value_object_type}: {reason}",
            code="INVALID_VALUE_OBJECT"
        )


class InvalidOperationException(DomainException):
    """无效操作异常"""
    
    def __init__(self, operation: str, reason: str):
        self.operation = operation
        super().__init__(
            message=f"Operation '{operation}' is invalid: {reason}",
            code="INVALID_OPERATION"
        )


class InvalidStateTransitionException(DomainException):
    """无效状态转换异常"""
    
    def __init__(self, entity: str, from_state: str, to_state: str, reason: Optional[str] = None):
        self.entity = entity
        self.from_state = from_state
        self.to_state = to_state
        message = f"Invalid state transition for {entity} from '{from_state}' to '{to_state}'"
        if reason:
            message += f": {reason}"
        super().__init__(
            message=message,
            code="INVALID_STATE_TRANSITION"
        )


class AggregateVersionMismatchException(DomainException):
    """聚合版本不匹配异常（用于乐观锁）"""
    
    def __init__(
        self,
        aggregate_type: str,
        aggregate_id: Any,
        expected_version: int,
        actual_version: int
    ):
        self.aggregate_type = aggregate_type
        self.aggregate_id = aggregate_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(
            message=(
                f"{aggregate_type} with id '{aggregate_id}' version mismatch. "
                f"Expected: {expected_version}, Actual: {actual_version}"
            ),
            code="AGGREGATE_VERSION_MISMATCH"
        )


class DuplicateEntityException(DomainException):
    """实体重复异常"""
    
    def __init__(self, entity_type: str, identifier_field: str, identifier_value: Any):
        self.entity_type = entity_type
        self.identifier_field = identifier_field
        self.identifier_value = identifier_value
        super().__init__(
            message=f"{entity_type} with {identifier_field} '{identifier_value}' already exists",
            code="DUPLICATE_ENTITY"
        )


class DomainEventException(DomainException):
    """领域事件异常"""
    
    def __init__(self, event_type: str, message: str):
        self.event_type = event_type
        super().__init__(
            message=f"Domain event '{event_type}' error: {message}",
            code="DOMAIN_EVENT_ERROR"
        )


class SpecificationNotSatisfiedException(DomainException):
    """规约不满足异常"""
    
    def __init__(self, specification: str, entity: Any):
        self.specification = specification
        self.entity = entity
        super().__init__(
            message=f"Entity does not satisfy specification '{specification}'",
            code="SPECIFICATION_NOT_SATISFIED"
        )
