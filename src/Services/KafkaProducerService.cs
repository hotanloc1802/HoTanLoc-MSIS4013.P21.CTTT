// Trong file Services/KafkaProducerService.cs
using Confluent.Kafka;
using System.Text.Json;
using Books.Api.Docker.Dtos;
using Microsoft.Extensions.Options; // Để đọc cấu hình

namespace Books.Api.Services;

public class KafkaProducerSettings
{
    public string BootstrapServers { get; set; } = string.Empty;
}

public class KafkaProducerService : IKafkaProducerService, IDisposable
{
    private readonly IProducer<Null, string>? _producer; // Cho phép _producer có thể null ban đầu
    private readonly ILogger<KafkaProducerService> _logger;
    private readonly string _bootstrapServers;

    public KafkaProducerService(IOptions<KafkaProducerSettings> settings, ILogger<KafkaProducerService> logger)
    {
        _logger = logger;
        _bootstrapServers = settings.Value.BootstrapServers;
        _logger.LogInformation("[KAFKA_PRODUCER] Constructor called. BootstrapServers from config: '{BootstrapServers}'", _bootstrapServers);

        if (string.IsNullOrEmpty(_bootstrapServers))
        {
            _logger.LogError("[KAFKA_PRODUCER] BootstrapServers is NULL or EMPTY. Kafka producer will NOT be configured or used.");
            return;
        }

        var producerConfig = new ProducerConfig
        {
            BootstrapServers = _bootstrapServers,
            // THÊM DÒNG NÀY ĐỂ BẬT DEBUG LOG CHO LIBRDKAFKA
            Debug = "broker,protocol,msg"
            // Bạn có thể thử "all" để có log tối đa, nhưng "broker,protocol,msg" thường hữu ích
        };

        try
        {
            _producer = new ProducerBuilder<Null, string>(producerConfig).Build();
            _logger.LogInformation("[KAFKA_PRODUCER] Producer built successfully with servers: {BootstrapServers}", _bootstrapServers);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "[KAFKA_PRODUCER] Error building Kafka producer with servers: {BootstrapServers}", _bootstrapServers);
        }
    }

    public async Task ProduceBookEventAsync(string topic, BookEvent bookEvent, CancellationToken cancellationToken = default)
    {
        if (_producer == null)
        {
            _logger.LogWarning("[KAFKA_PRODUCER] Producer is not initialized (likely due to missing/bad config or build error). Cannot send event for BookId: {BookId}", bookEvent.BookId);
            return; // Không gửi nếu producer không được khởi tạo
        }

        _logger.LogInformation("[KAFKA_PRODUCER] Attempting to produce event for BookId: {BookId}, EventType: {EventType} to topic {Topic}",
            bookEvent.BookId, bookEvent.EventType, topic);

        try
        {
            var messageValue = JsonSerializer.Serialize(bookEvent);
            var message = new Message<Null, string> { Value = messageValue };

            _logger.LogInformation("[KAFKA_PRODUCER] Serialized message: {MessageValue}", messageValue);

            // ProduceAsync có thể ném ProduceException nếu có lỗi trong quá trình gửi
            var deliveryResult = await _producer.ProduceAsync(topic, message, cancellationToken);

            _logger.LogInformation("[KAFKA_PRODUCER] Successfully sent book event to Kafka topic {Topic} - Partition: {Partition}, Offset: {Offset}, BookId: {BookId}, EventType: {EventType}",
                topic,
                deliveryResult.Partition,
                deliveryResult.Offset,
                bookEvent.BookId,
                bookEvent.EventType);
        }
        catch (ProduceException<Null, string> e)
        {
            // Lỗi này xảy ra khi Kafka broker từ chối message hoặc có vấn đề mạng nghiêm trọng khi gửi
            _logger.LogError(e, "[KAFKA_PRODUCER] Failed to deliver message (ProduceException) for BookId {BookId} to topic {Topic}. Reason: {Reason}. Kafka Error: {ErrorObject}",
                bookEvent.BookId, topic, e.Error.Reason, e.Error.ToString());
        }
        catch (JsonException jsonEx)
        {
            _logger.LogError(jsonEx, "[KAFKA_PRODUCER] Failed to serialize BookEvent for BookId {BookId}", bookEvent.BookId);
        }
        catch (Exception ex) // Bắt các lỗi không mong muốn khác
        {
            _logger.LogError(ex, "[KAFKA_PRODUCER] Unexpected error producing message for BookId {BookId} to topic {Topic}",
                bookEvent.BookId, topic);
        }
    }

    public void Dispose()
    {
        if (_producer != null)
        {
            _logger.LogInformation("[KAFKA_PRODUCER] Flushing producer...");
            _producer.Flush(TimeSpan.FromSeconds(10));
            _producer.Dispose();
            _logger.LogInformation("[KAFKA_PRODUCER] Producer disposed.");
        }
        GC.SuppressFinalize(this);
    }
}