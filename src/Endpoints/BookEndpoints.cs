using Books.Api.Services;

namespace Books.Api.Docker.Endpoints;

public static class BookEndpoints
{
    public static void MapBookEndpoints(this IEndpointRouteBuilder app)
    {
        var bookGroup = app.MapGroup("books");

        bookGroup.MapGet("", GetAllBooks).WithName(nameof(GetAllBooks));

        bookGroup.MapGet("{id}", GetBookById).WithName(nameof(GetBookById));

        bookGroup.MapPost("", CreateBook).WithName(nameof(CreateBook));

        bookGroup.MapPut("{id}", UpdateBook).WithName(nameof(UpdateBook));

        bookGroup.MapDelete("{id}", DeleteBookById).WithName(nameof(DeleteBookById));
    }

    public static async Task<IResult> GetAllBooks(
        IBookService bookService,
        CancellationToken cancellationToken)
    {
        var books = await bookService.GetBooksAsync(cancellationToken);

        return Results.Ok(books.Select(b => b.ToResponseDto()));
    }

    public static async Task<IResult> GetBookById(
         int id,
         IBookService bookService,
         IRedisCacheService cacheService,
         CancellationToken cancellationToken)
    {
        var cacheKey = $"book_{id}";

        var response = await cacheService.GetDataAsync<BookResponse>(
            cacheKey,
            cancellationToken);

        if (response is not null)
        {
            return Results.Ok(response);
        }

        var book = await bookService.GetBookByIdAsync(id, cancellationToken);

        if (book is null)
        {
            return Results.NotFound();
        }

        response = book.ToResponseDto();

        await cacheService.SetDataAsync<BookResponse>(
            cacheKey,
            response,
            cancellationToken);

        return Results.Ok(response);
    }

    public static async Task<IResult> CreateBook(
    CreateBookRequest request,
    IBookService bookService,
    IKafkaProducerService kafkaProducerService, // Thêm DI
    CancellationToken cancellationToken)
    {

        var book = request.ToEntity();
        book.Id = await bookService.CreateBookAsync(book, cancellationToken);

        // Gửi sự kiện BookCreated
        var bookCreatedEvent = new BookEvent
        {
            BookId = book.Id,
            EventType = "BookCreated",
            Timestamp = DateTime.UtcNow
        };
        await kafkaProducerService.ProduceBookEventAsync("book_events", bookCreatedEvent, cancellationToken);

        return Results.CreatedAtRoute(
            nameof(GetBookById),
            new { id = book.Id },
            book.ToResponseDto()); // Trả về DTO thay vì entity
    }

    // Trong BookEndpoints.cs

    public static async Task<IResult> UpdateBook(
        int id, // id từ route vẫn cần thiết để tạo bookEntity với đúng Id
        UpdateBookRequest request,
        IBookService bookService,
        IRedisCacheService cacheService,
        IKafkaProducerService kafkaProducerService,
        CancellationToken cancellationToken)
    {
        try
        {
            var cacheKey = $"book_{id}";

            // Tạo entity 'Book' từ request.
            // Quan trọng: Phương thức ToEntity() của bạn cần đảm bảo gán 'id' từ route vào đối tượng Book.
            var bookEntity = request.ToEntity(id);

            // Gọi UpdateBookAsync với đúng tham số theo interface
            // BookService.UpdateBookAsync sẽ chịu trách nhiệm kiểm tra xem sách có tồn tại không
            // (dựa vào bookEntity.Id) và ném KeyNotFoundException nếu không tìm thấy.
            await bookService.UpdateBookAsync(bookEntity, cancellationToken);

            // Nếu không có exception, coi như việc tìm và xử lý update đã diễn ra
            await cacheService.RemoveDataAsync(cacheKey, cancellationToken);

            var bookUpdatedEvent = new BookEvent
            {
                BookId = id, // Hoặc bookEntity.Id
                EventType = "BookUpdated",
                Timestamp = DateTime.UtcNow
            };
            await kafkaProducerService.ProduceBookEventAsync("book_events", bookUpdatedEvent, cancellationToken);

            return Results.NoContent();
        }
        catch (KeyNotFoundException) // Bắt lỗi nếu sách không tìm thấy để cập nhật (ném từ BookService)
        {
            return Results.NotFound($"Book with id {id} not found.");
        }
        catch (Exception ex) // Bắt các lỗi không mong muốn khác
        {
            // Log lỗi chi tiết ở đây (ví dụ: _logger.LogError(ex, "Error updating book {BookId}", id);)
            return Results.Problem($"An error occurred while updating the book with id {id}.", statusCode: StatusCodes.Status500InternalServerError);
        }
    }
    public static async Task<IResult> DeleteBookById(
            int id,
            IBookService bookService,
            IRedisCacheService cacheService,
            CancellationToken cancellationToken)
    {
        try
        {
            var cacheKey = $"book_{id}";

            await bookService.DeleteBookByIdAsync(id, cancellationToken);

            await cacheService.RemoveDataAsync(cacheKey, cancellationToken);

            return Results.NoContent();
        }
        catch (Exception ex)
        {
            return Results.NotFound(ex.Message);
        }
    }
}
