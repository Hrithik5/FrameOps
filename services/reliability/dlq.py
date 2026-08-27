"""DLQ simulation — Spec SQS redelivery."""

from dataclasses import dataclass, field


@dataclass
class SQSMessage:
    body: str
    receive_count: int = 0
    max_receive_count: int = 5


@dataclass
class DLQ:
    messages: list[SQSMessage] = field(default_factory=list)


@dataclass
class Queue:
    name: str
    messages: list[SQSMessage] = field(default_factory=list)
    dlq: DLQ = field(default_factory=DLQ)

    def receive(self) -> SQSMessage | None:
        if not self.messages:
            return None
        msg = self.messages[0]
        msg.receive_count += 1
        if msg.receive_count > self.dlq_threshold():
            self.dlq.messages.append(msg)
            self.messages.pop(0)
            return None
        return msg

    def dlq_threshold(self) -> int:
        return 5

    def ack(self, msg: SQSMessage) -> None:
        if msg in self.messages:
            self.messages.remove(msg)

    def nack(self, msg: SQSMessage) -> None:
        # Redelivery — if exceeds threshold, DLQ handles on next receive
        pass
