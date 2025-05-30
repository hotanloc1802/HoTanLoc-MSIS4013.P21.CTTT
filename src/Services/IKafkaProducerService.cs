using Books.Api.Docker.Dtos; // Hoặc namespace của BookEvent

namespace Books.Api.Services;

public interface IKafkaProducerService
{
    Task ProduceBookEventAsync(string topic, BookEvent bookEvent, CancellationToken cancellationToken = default);
}