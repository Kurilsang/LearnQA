import asyncio


class HandlerRegistry:
    def __init__(self):
        self._handlers = {}

    def register(self, name=None, func=None):
        if func is None and callable(name):
            func = name
            self._handlers[func.__name__] = func
            return func
        if func is None:
            return lambda f: self.register(name, f)
        self._handlers[name] = func
        return func

    def get(self, name: str):
        return self._handlers.get(name)

    def has(self, name: str) -> bool:
        return name in self._handlers

    async def execute(self, name: str, *args, **kwargs):
        handler = self.get(name)
        if handler is None:
            raise KeyError(f"Handler '{name}' not found")
        if asyncio.iscoroutinefunction(handler):
            return await handler(*args, **kwargs)
        return handler(*args, **kwargs)


registry = HandlerRegistry()
