"""
Kafka consumer for real-time market data streaming.
Processes incoming tick data from market data providers.
"""
import asyncio
import json
from typing import Callable, Optional, Any
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from ...core.config import get_settings
from ...utils.logging import get_logger


settings = get_settings()
logger = get_logger(__name__)


class KafkaMarketDataConsumer:
    """Kafka consumer for market data."""

    def __init__(
        self,
        topic: Optional[str] = None,
        group_id: Optional[str] = None
    ) -> None:
        """
        Initialize Kafka consumer.

        Args:
            topic: Kafka topic to consume from
            group_id: Consumer group ID
        """
        self.topic = topic or settings.KAFKA_MARKET_DATA_TOPIC
        self.group_id = group_id or settings.KAFKA_CONSUMER_GROUP
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.consumer: Optional[AIOKafkaConsumer] = None
        self.running = False

    async def start(self) -> None:
        """Start Kafka consumer."""
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await self.consumer.start()
        self.running = True
        logger.info(f"Kafka consumer started for topic: {self.topic}")

    async def stop(self) -> None:
        """Stop Kafka consumer."""
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def consume(
        self,
        callback: Callable[[dict], Any]
    ) -> None:
        """
        Consume messages from Kafka and process with callback.

        Args:
            callback: Async function to process each message
        """
        if not self.consumer:
            raise RuntimeError("Consumer not started")

        try:
            async for message in self.consumer:
                if not self.running:
                    break

                try:
                    await callback(message.value)
                except Exception as e:
                    logger.error(
                        f"Error processing message: {e}",
                        topic=message.topic,
                        partition=message.partition,
                        offset=message.offset
                    )

        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            raise


class KafkaMarketDataProducer:
    """Kafka producer for market data."""

    def __init__(self) -> None:
        """Initialize Kafka producer."""
        self.bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """Start Kafka producer."""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
        logger.info("Kafka producer started")

    async def stop(self) -> None:
        """Stop Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")

    async def send(
        self,
        topic: str,
        message: dict,
        key: Optional[str] = None
    ) -> None:
        """
        Send message to Kafka topic.

        Args:
            topic: Kafka topic
            message: Message to send
            key: Optional message key
        """
        if not self.producer:
            raise RuntimeError("Producer not started")

        try:
            key_bytes = key.encode('utf-8') if key else None
            await self.producer.send(topic, value=message, key=key_bytes)
            logger.debug(f"Message sent to topic: {topic}")
        except KafkaError as e:
            logger.error(f"Error sending message to Kafka: {e}")
            raise

    async def send_market_data(self, tick_data: dict) -> None:
        """
        Send market data tick to Kafka.

        Args:
            tick_data: Tick data dictionary
        """
        symbol = tick_data.get('symbol')
        await self.send(
            settings.KAFKA_MARKET_DATA_TOPIC,
            tick_data,
            key=symbol
        )

    async def send_trade_execution(self, trade_data: dict) -> None:
        """
        Send trade execution to Kafka.

        Args:
            trade_data: Trade execution data
        """
        order_id = str(trade_data.get('order_id'))
        await self.send(
            settings.KAFKA_TRADE_EXECUTION_TOPIC,
            trade_data,
            key=order_id
        )


# Global Kafka instances
market_data_consumer = KafkaMarketDataConsumer()
market_data_producer = KafkaMarketDataProducer()
