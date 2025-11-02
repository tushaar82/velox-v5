"""Kafka consumer for real-time market data streaming."""
import asyncio
import json
from typing import Callable, Dict, List, Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from src.core.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class KafkaMarketDataConsumer:
    """Kafka consumer for market data."""

    def __init__(
        self,
        topics: List[str],
        group_id: str = "velox-trading-group",
    ):
        self.topics = topics
        self.group_id = group_id
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False
        self.message_handlers: Dict[str, List[Callable]] = {}

    async def start(self) -> None:
        """Start the Kafka consumer."""
        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=self.group_id,
                enable_auto_commit=True,
                auto_offset_reset="latest",
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            await self.consumer.start()
            self.running = True
            logger.info(
                "kafka_consumer_started",
                topics=self.topics,
                group_id=self.group_id,
            )
        except KafkaError as e:
            logger.error("kafka_consumer_start_failed", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        if self.consumer:
            self.running = False
            await self.consumer.stop()
            logger.info("kafka_consumer_stopped")

    def register_handler(self, topic: str, handler: Callable) -> None:
        """Register a message handler for a topic."""
        if topic not in self.message_handlers:
            self.message_handlers[topic] = []
        self.message_handlers[topic].append(handler)
        logger.info("kafka_handler_registered", topic=topic, handler=handler.__name__)

    async def consume(self) -> None:
        """Consume messages from Kafka."""
        if not self.consumer:
            raise RuntimeError("Consumer not started")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                topic = message.topic
                value = message.value

                logger.debug(
                    "kafka_message_received",
                    topic=topic,
                    partition=message.partition,
                    offset=message.offset,
                )

                # Call registered handlers for this topic
                if topic in self.message_handlers:
                    for handler in self.message_handlers[topic]:
                        try:
                            await handler(value)
                        except Exception as e:
                            logger.error(
                                "kafka_handler_error",
                                topic=topic,
                                handler=handler.__name__,
                                error=str(e),
                            )
        except Exception as e:
            logger.error("kafka_consume_error", error=str(e))
            raise

    async def run(self) -> None:
        """Run the consumer (start and consume)."""
        await self.start()
        try:
            await self.consume()
        finally:
            await self.stop()


class KafkaProducer:
    """Kafka producer for publishing market data."""

    def __init__(self):
        from aiokafka import AIOKafkaProducer

        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        try:
            from aiokafka import AIOKafkaProducer

            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self.producer.start()
            logger.info("kafka_producer_started")
        except KafkaError as e:
            logger.error("kafka_producer_start_failed", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("kafka_producer_stopped")

    async def send(self, topic: str, value: Dict) -> None:
        """Send a message to a Kafka topic."""
        if not self.producer:
            raise RuntimeError("Producer not started")

        try:
            await self.producer.send_and_wait(topic, value)
            logger.debug("kafka_message_sent", topic=topic)
        except Exception as e:
            logger.error("kafka_send_error", topic=topic, error=str(e))
            raise


# Global instances
market_data_consumer = KafkaMarketDataConsumer(
    topics=["market_ticks", "market_candles"],
)
market_data_producer = KafkaProducer()
