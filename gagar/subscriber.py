class Subscriber(object):
    """Base class for event handlers via on_*() methods."""

    def __getattr__(self, func_name):
        # still throw error when not getting an on_* attribute
        if 'on_' != func_name[:3]:
            raise AttributeError("'%s' object has no attribute '%s'"
                                 % (self.__class__.__name__, func_name))
        return lambda *args, **kwargs: None  # default handler does nothing


class MultiSubscriber(Subscriber):
    """Distributes method calls to multiple subscribers."""

    def __init__(self, *subs):
        self.subs = list(subs)

    def sub(self, subscriber):
        self.subs.append(subscriber)
        return subscriber

    def __getattr__(self, func_name):
        super(MultiSubscriber, self).__getattr__(func_name)

        def wrapper(*args, **kwargs):
            for sub in self.subs:
                handler = getattr(sub, func_name, None)
                if handler:
                    handler(*args, **kwargs)

        return wrapper
