def create_message_bus(type='amqp', *args, **kwargs):
    if type.lower() == 'amqp':
        from nowin_core.message_bus.amqp import AMQPMessageBus
        return AMQPMessageBus(*args, **kwargs)
    elif type.lower() == 'pb':
        from nowin_core.message_bus.pb import PBMessageBus
        return PBMessageBus(*args, **kwargs)
    elif type.lower() == 'stomp':
        from nowin_core.message_bus.stomp import STOMPMessageBus
        return STOMPMessageBus(*args, **kwargs)
