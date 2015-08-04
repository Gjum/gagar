"""
Example usage

Also available as highlighted markdown:
https://gist.github.com/Gjum/10bd136ca25304f30e02

Minimal example:
Reload when '.' key is pressed.

    class Leaderboard(Subscriber, Reloadable):
        # There is no __init__() with args and no state, so
        # neither capture_args() nor _persistent_attributes
        # are needed.

        # We want to reload somehow, so we use a key press event for this
        def on_key_pressed(self, val, char):
            if char == '.':  # reload when pressing '.'
                self.reload()  # note: does not check for syntax/runtime errors

        def on_draw_hud(self, c, w):
            # ...

Complex example:
Auto-reload every second, keeping init args and instance state.

    class MassGraph(Subscriber, Reloadable):
        _persistent_attributes = ['graph']  # restore graph after reload

        def __init__(self, client):
            # restore client after reload
            # (when calling __init__, client is supplied as argument)
            self.capture_args(locals())

            self.reload_timer = 0  # used below

            self.client = client  # set via init arg
            self.graph = []  # should be kept between reloads

        def on_respawn(self):
            # ...

        def on_world_update_post(self):
            # ...

            self.reload_timer += 1
            if self.reload_timer > 25:  # world updates occur 25x per second
                # Do not crash if the reload fails.
                # Note that this does not catch all syntax errors
                # and still no runtime errors.
                self.try_reload()

        def on_draw_hud(self, c, w):
            # ...
"""
import importlib, sys, types


class Reloadable(object):
    """Makes inheriting class instances reloadable."""

    _persistent_attributes = []  # will be kept when reloading

    def capture_args(self, init_args):
        """
        Capture original args for calling init on reload.
        An ancestor should call this in their init with locals() as argument
        before creating any more local variables:

        >>> class Foo(Reloadable):
        >>>     def __init__(self, foo, bar=123):
        >>>         super(self.__class__, self).__init__()
        >>>         self.foo = foo * bar  # just uses `self`, thus not creating a local var
        >>>         self.capture_args(locals())  # captures self, foo, bar
        >>>         tmp = bar ** 2  # creates local var `tmp`
        >>>         # ...
        """
        self._init_args = dict(init_args)
        for k in list(self._init_args.keys()):
            if k == 'self' or k[:2] == '__':
                del self._init_args[k]

    def reload(self, new_module=None):
        """
        Reloads the containing module and replaces all instance attributes
        (monkey-patching, see https://filippo.io/instance-monkey-patching-in-python/ )
        while keeping the attributes in _persistent_attributes.
        """
        if not new_module:
            new_module = importlib.reload(sys.modules[self.__module__])
        new_class = getattr(new_module, self.__class__.__name__)
        persistent = {k: getattr(self, k) for k in self._persistent_attributes}
        for new_attr_name in dir(new_class):
            if new_attr_name in ('__class__', '__dict__', '__weakref__'):
                continue  # do not copy '__dict__', '__weakref__'; copy '__class__' below
            new_attr = getattr(new_class, new_attr_name)
            try:  # some attributes are instance methods, bind them to `self`
                new_attr = types.MethodType(new_attr, self)
            except TypeError:
                pass
            setattr(self, new_attr_name, new_attr)
        setattr(self, '__class__', new_class)
        new_class.__init__(self, **getattr(self, '_init_args', {}))
        for k, v in persistent.items():
            setattr(self, k, v)

    def try_reload(self):
        """
        Try to reload the containing module.
        If an exception is thrown in the process, catch and return it.
        Useful to catch syntax errors.

        :return the thrown exception if not successfully reloaded, None otherwise
        """
        try:
            self.reload()
        except Exception as e:
            return e
