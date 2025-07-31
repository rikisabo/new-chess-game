
_listeners: dict[str, list] = {}

def subscribe(topic: str, fn):
    """Subscribe a function to listen for events on a specific topic."""
    _listeners.setdefault(topic, []).append(fn)

def unsubscribe(topic: str, fn):
    """Unsubscribe a function from a specific topic."""
    if topic in _listeners and fn in _listeners[topic]:
        _listeners[topic].remove(fn)
        # Clean up empty topic lists
        if not _listeners[topic]:
            del _listeners[topic]

def publish(topic: str, data=None):
    """Publish an event to all subscribers of a topic."""
    for fn in _listeners.get(topic, []):
        fn(data)

def clear_topic(topic: str):
    """Remove all subscribers from a specific topic."""
    if topic in _listeners:
        del _listeners[topic]

def clear_all():
    """Remove all subscribers from all topics."""
    _listeners.clear()
