from Subscriber import Subscriber
from KFC_Py.enums.EventType import EventType
class MessageBroker:
    def __init__(self):
        self.subscribers = {}  

    def subscribe(self, event_type: EventType, subscriber: Subscriber):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(subscriber)

    def publish(self, event_type: EventType,data):
        if event_type in self.subscribers:
            for sub in self.subscribers[event_type]:
                sub.handle_event(event_type, data)
