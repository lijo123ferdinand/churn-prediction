from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import (
    KafkaSource,
    KafkaOffsetsInitializer
)
from pyflink.common.serialization import SimpleStringSchema
from pyflink.common.typeinfo import Types

def main():
    env = StreamExecutionEnvironment.get_execution_environment()

    # Create Kafka source
    source = (
        KafkaSource.builder()
        .set_bootstrap_servers("localhost:9092")
        .set_topics("user_events")
        .set_group_id("flink-user-events-consumer")
        .set_starting_offsets(KafkaOffsetsInitializer.earliest())
        .set_value_only_deserializer(SimpleStringSchema())
        .build()
    )

    # Add source to Flink environment
    ds = env.from_source(source, watermark_strategy=None, type_info=Types.STRING())

    # Print messages to stdout
    ds.print()

    env.execute("Kafka User Events Consumer")

if __name__ == "__main__":
    main()
