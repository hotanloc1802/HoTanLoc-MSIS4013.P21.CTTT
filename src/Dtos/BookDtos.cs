namespace Books.Api.Docker.Dtos;

public sealed record CreateBookRequest(
    string Title, 
    string ISBN, 
    string Description, 
    string Author);

public sealed record BookResponse(
    int Id,
    string Title,
    string ISBN,
    string Description,
    string Author);

public sealed record UpdateBookRequest(
    string Title,
    string ISBN,
    string Description,
    string Author);
public class BookEvent
{
    public int BookId { get; set; }
    public string EventType { get; set; } = string.Empty; // Ví dụ: "BookCreated", "BookUpdated"
    public DateTime Timestamp { get; set; }
}
