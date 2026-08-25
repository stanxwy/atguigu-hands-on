from abc import ABC, abstractmethod


class WebSearch(ABC):
    
    @abstractmethod
    async def search_web(self, query): ...