from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer
from pyflink.common.typeinfo import Types
from pyflink.common.watermark_strategy import WatermarkStrategy

def main():
    env = StreamExecutionEnvironment.get_execution_environment()

    source = (
        KafkaSource.builder()
        .set_bootstrap_servers("localhost:9092")
        .set_topics("test-topic")
        .set_group_id("flink_consumer")
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    ds = env.from_source(
        source,
        watermark_strategy=WatermarkStrategy.for_monotonous_timestamps(),
        source_name="kafka_source",
        type_info=Types.STRING()
    )

    ds.print()

    env.execute("Kafka Consumer Job")
