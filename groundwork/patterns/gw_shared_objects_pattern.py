from groundwork.patterns.gw_base_pattern import GwBasePattern


class GwSharedObjectsPattern(GwBasePattern):
    """
    Pattern, which provides access to shared object functionality.

    Use shared objects to provide access for other plugins to objects, which are created by this plugin.
    Or use it to get access to objects provided by other plugins.

    Common use cases are stores, which handle business logic and database abstraction. E.g. a user store.

    Provided function:

     * self.shared_objects.register()
     * self.shared_objects.unregister()
     * self.shared_objects.get()

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self.app, "shared_objects"):
            self.app.shared_objects = SharedObjectsListApplication(self.app)
        self.shared_objects = SharedObjectsListPlugin(self)

    def activate(self):
        pass

    def deactivate(self):
        pass


class SharedObjectsListPlugin:
    """
    Cares about plugin function for shared objects on plugin level.

    The class mainly directs most function calls to the ShareObjectApplication class, which is initiated on
    application level.
    """
    def __init__(self, plugin):
        """
        :param plugin: initiated plugin object
        """
        self.plugin = plugin
        self.app = plugin.app
        self.log = plugin.log
        # Let's register a receiver, which cares about the deactivation process of shared objects for this plugin.
        # We do it after the original plugin deactivation, so we can be sure that the registered function is the last
        # one which cares about shared objects for this plugin.
        self.plugin.signals.connect(receiver="%s_shared_objects_deactivation" % self.plugin.name,
                                    signal="plugin_deactivate_post",
                                    function=self.__deactivate_shared_objects,
                                    description="Deactivate documents for %s" % self.plugin.name,
                                    sender=self.plugin)

        self.log.debug("Shared objects for plugin %s initialised" % self.plugin.name)

    def __deactivate_shared_objects(self, plugin, *args, **kwargs):
        """
        Callback, which gets executed, if the signal "plugin_deactivate_post" was send by the plugin.
        """
        shared_objects = self.get()
        for shared_object in shared_objects.keys():
            self.unregister(shared_object)

    def register(self, name, description, obj):
        """
        Registers a new shared object.

        :param name: Unique name for shared object
        :type name: str
        :param description: Description of shared object
        :type description: str
        :param obj: The object, which shall be shared
        :type obj: any type
        """
        return self.app.shared_objects.register(name, description, obj, self.plugin)

    def unregister(self, shared_object):
        """
        Unregisters an already registered shared object.

        :param shared_object: name of the shared object
        :type shared_object: str
        """
        return self.app.shared_objects.unregister(shared_object)

    def get(self, name=None):
        """
        Returns requested shared objects.

        :param name: Name of a request shared object
        :type name: str or None
        """
        return self.app.shared_objects.get(name, self.plugin)

    def __getattr__(self, item):
        """
        Catches unknown function/attribute calls and delegates them to SharedObjectsListApplication
        """

        def method(*args, **kwargs):
            func = getattr(self.app.shared_objects, item, None)
            if func is None:
                raise AttributeError("SharedObjectsList does not have an attribute called %s" % item)
            return func(*args, plugin=self.plugin, **kwargs)

        return method


class SharedObjectsListApplication:
    """
    Cares about shared objects on application level.
    """
    def __init__(self, app):
        """
        :param app: groundwork application object, for which shared objects shall be activated on application level.
        """
        self.app = app
        self.log = app.log
        self._shared_objects = {}
        self.log.debug("Application shared objects initialised")

    def get(self, name=None, plugin=None):
        """
        Returns requested shared objects.

        :param name: Name of a request shared object
        :type name: str or None
        :param plugin: Plugin, which has registered the requested shared object
        :type plugin: GwBasePattern instance or None
        """
        if plugin is not None:
            if name is None:
                shared_objects_list = {}
                for key in self._shared_objects.keys():
                    if self._shared_objects[key].plugin == plugin:
                        shared_objects_list[key] = self._shared_objects[key]
                return shared_objects_list
            else:
                if name in self._shared_objects.keys():
                    if self._shared_objects[name].plugin == plugin:
                        return self._shared_objects[name]
                    else:
                        return None
                else:
                    return None
        else:
            if name is None:
                return self._shared_objects
            else:
                if name in self._shared_objects.keys():
                    return self._shared_objects[name]
                else:
                    return None

    def register(self, name, description, obj, plugin):
        """
        Registers a new shared object.

        :param name: Unique name for shared object
        :type name: str
        :param description: Description of shared object
        :type description: str
        :param obj: The object, which shall be shared
        :type obj: any type
        :param plugin: Plugin, which registers the new shared object
        """
        if name in self._shared_objects.keys():
            raise SharedObjectExistException("Shared Object %s already registered by %s"
                                             % (name, self._shared_objects[name].plugin.name))

        new_shared_object = SharedObject(name, description, obj, plugin)
        self._shared_objects[name] = new_shared_object
        self.log.debug("Shared object registered: %s" % name)
        return new_shared_object

    def unregister(self, shared_object):
        """
        Unregisters an existing shared object, so that this shared object is no longer available.

        This function is mainly used during plugin deactivation.

        :param shared_object: Name of the shared_object
        """
        if shared_object not in self._shared_objects.keys():
            self.log.warning("Can not unregister shared object %s" % shared_object)
        else:
            del (self._shared_objects[shared_object])
            self.log.debug("Shared object %s got unregistered" % shared_object)


class SharedObject:
    """
    SharedObject class, which stores the objects itself besides meta data like an unique name, a description and the
    plugin, which registers the shared object.
    """
    def __init__(self, name, description, obj, plugin):
        """
        :param name: Unique name of the shared object
        :param description: Description
        :param obj: The object itself, which gets shared
        :param plugin: The plugin, which registered this shared object
        """
        self.name = name
        self.description = description
        self.obj = obj
        self.plugin = plugin


class SharedObjectExistException(BaseException):
    pass
