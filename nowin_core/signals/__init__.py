from nowin_core.patterns.observer import Subject as _Subject

#: called when user is created
user_created_event = _Subject()

#: called when user is activated
user_activated_event = _Subject()

#: called when chat-room settings are changed
chatroom_setting_changed = _Subject()
