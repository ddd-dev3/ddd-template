from abc import ABC


class DomainService(ABC):
    """领域服务的基类。
    
    领域服务用于：
    - 封装不属于任何实体或值对象的领域逻辑
    - 协调多个聚合之间的操作
    - 实现复杂的业务规则
    """
    pass

