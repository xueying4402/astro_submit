import copy

from lib import config

class WFGBasicBlock:
    def __init__(self, block_id) -> None:
        self._block_id = block_id
        self._has_reset = False
        self._has_add_temp = False
        self._has_add_new_wfg = False
    
    @property
    def block_id(self) -> int:
        return self._block_id
    
    @block_id.setter
    def block_id(self, block_id: int) -> None:
        self._block_id = block_id
        
    @property
    def has_reset(self) -> bool:
        return self._has_reset

    @has_reset.setter
    def has_reset(self, has_reset: bool) -> None:
        self._has_reset = has_reset

    @property
    def has_add_temp(self) -> bool:
        return self._has_add_temp

    @has_add_temp.setter
    def has_add_temp(self, has_add_temp: bool) -> None:
        self._has_add_temp = has_add_temp

    @property
    def has_add_new_wfg(self) -> bool:
        return self._has_add_new_wfg

    @has_add_new_wfg.setter
    def has_add_new_wfg(self, has_add_new_wfg: bool) -> None:
        self._has_add_new_wfg = has_add_new_wfg

    def copy(self) -> 'WFGBasicBlock':
        return copy.deepcopy(self)

    def __eq__(self, other) -> bool:
        if not isinstance(other, WFGBasicBlock):
            return False
        return self._block_id == other._block_id

    def __hash__(self) -> int:
        return hash(self._block_id)

    def __str__(self) -> str:
        return str(self._block_id)