$apiUrl = "http://localhost:5000/books"

# Danh sách 50 tựa sách mẫu (có thể bổ sung hoặc thay đổi)
$titles = @(
    "Introduction to Algorithms",
    "The Pragmatic Programmer",
    "Design Patterns: Elements of Reusable Object-Oriented Software",
    "Effective Java",
    "You Don't Know JS",
    "Refactoring: Improving the Design of Existing Code",
    "The Clean Coder",
    "JavaScript: The Good Parts",
    "Python Crash Course",
    "Eloquent JavaScript",
    "Cracking the Coding Interview",
    "Code Complete",
    "Head First Design Patterns",
    "Working Effectively with Legacy Code",
    "Domain-Driven Design",
    "Agile Software Development, Principles, Patterns, and Practices",
    "Test Driven Development: By Example",
    "Continuous Delivery",
    "The Mythical Man-Month",
    "Structure and Interpretation of Computer Programs",
    "Patterns of Enterprise Application Architecture",
    "JavaScript Patterns",
    "The Art of Computer Programming",
    "Algorithms",
    "Programming Pearls",
    "Clean Architecture",
    "The Phoenix Project",
    "Release It!",
    "Microservices Patterns",
    "Building Microservices",
    "Docker Deep Dive",
    "Kubernetes Up & Running",
    "Site Reliability Engineering",
    "Artificial Intelligence: A Modern Approach",
    "The C Programming Language",
    "Effective C++",
    "Designing Data-Intensive Applications",
    "The DevOps Handbook",
    "You Don't Know JS: Scope & Closures",
    "Cracking the PM Interview",
    "Lean Software Development",
    "Introduction to the Theory of Computation",
    "Programming Rust",
    "Learning Python",
    "Pro Git",
    "The Go Programming Language",
    "Head First Java",
    "Computer Networks"
)

# Tác giả tương ứng cho 50 cuốn (có thể trùng lặp)
$authors = @(
    "Thomas H. Cormen",
    "Andrew Hunt",
    "Erich Gamma",
    "Joshua Bloch",
    "Kyle Simpson",
    "Martin Fowler",
    "Robert C. Martin",
    "Douglas Crockford",
    "Eric Matthes",
    "Marijn Haverbeke",
    "Gayle Laakmann McDowell",
    "Steve McConnell",
    "Eric Freeman",
    "Michael Feathers",
    "Eric Evans",
    "Robert C. Martin",
    "Kent Beck",
    "Jez Humble",
    "Frederick P. Brooks Jr.",
    "Harold Abelson",
    "Martin Fowler",
    "Stoyan Stefanov",
    "Donald E. Knuth",
    "Robert Sedgewick",
    "Jon Bentley",
    "Robert C. Martin",
    "Gene Kim",
    "Michael T. Nygard",
    "Chris Richardson",
    "Sam Newman",
    "Nigel Poulton",
    "Kelsey Hightower",
    "Betsy Beyer",
    "Stuart Russell",
    "Brian W. Kernighan",
    "Scott Meyers",
    "Martin Kleppmann",
    "Gene Kim",
    "Kyle Simpson",
    "Gayle Laakmann McDowell",
    "Mary Poppendieck",
    "Michael Sipser",
    "Jim Blandy",
    "Mark Lutz",
    "Scott Chacon",
    "Alan A. A. Donovan",
    "Kathy Sierra",
    "Andrew S. Tanenbaum"
)

# Mô tả ngắn gọn 50 cuốn sách
$descriptions = @(
    "Comprehensive coverage of modern algorithms and data structures.",
    "Tips and best practices for pragmatic software development.",
    "A catalog of simple and succinct software design patterns.",
    "A guide to best practices and features of the Java language.",
    "A deep dive into JavaScript language features and quirks.",
    "A practical guide to refactoring legacy codebases.",
    "Professional ethics and discipline for software developers.",
    "An overview of the good parts of JavaScript language.",
    "A fast-paced introduction to Python programming.",
    "Modern introduction to JavaScript for beginners and professionals.",
    "Preparation book for technical coding interviews.",
    "Software construction best practices and techniques.",
    "Introduction to design patterns with a visually rich style.",
    "How to work effectively with legacy code.",
    "Strategic design and modeling in software development.",
    "Agile principles and software craftsmanship.",
    "Guide to test-driven development with examples.",
    "Strategies for continuous software delivery and deployment.",
    "Classic book about software project management challenges.",
    "Foundations of computer programming using Scheme language.",
    "Patterns to solve common enterprise software challenges.",
    "Common JavaScript design patterns for cleaner code.",
    "Comprehensive volume on algorithms by a pioneer author.",
    "Algorithm design and analysis fundamentals.",
    "Classic essays on programming and software engineering.",
    "Guidelines for creating maintainable software architecture.",
    "A novel approach to IT operations and DevOps principles.",
    "Practical advice for building reliable software systems.",
    "Comprehensive guide to microservice design patterns.",
    "Techniques and best practices for building microservices.",
    "Deep dive into Docker container technology.",
    "Guide to Kubernetes architecture and usage.",
    "Practices for managing large-scale production systems.",
    "Widely used AI textbook covering fundamentals and techniques.",
    "The foundational book for C programming language.",
    "Effective programming techniques for C++ developers.",
    "How to design and build scalable data systems.",
    "Practical guide for implementing DevOps principles.",
    "Explores closures and scope in JavaScript deeply.",
    "Insights into product management and career advice.",
    "Lean principles applied to software development.",
    "Introduction to formal languages and automata theory.",
    "Comprehensive guide to Rust programming language.",
    "In-depth Python programming guide.",
    "Comprehensive Git version control book.",
    "Complete guide to Go programming language.",
    "Beginner-friendly Java programming with Head First style.",
    "Comprehensive overview of computer networking concepts."
)

for ($i = 0; $i -lt 50; $i++) {
    $book = @{
        title = $titles[$i]
        isbn = "978-1-23456-" + $i.ToString("D4")  # Giả lập ISBN 13 ký tự
        description = $descriptions[$i]
        author = $authors[$i]
    }

    $json = $book | ConvertTo-Json -Depth 3
    Write-Host "Sending book $($i+1): $($book.title)..."

    try {
        Invoke-RestMethod -Uri $apiUrl -Method POST -Body $json -ContentType "application/json"
        Write-Host "Done.`n"
    } catch {
        Write-Host "Failed to send book $($i+1). Error: $($_.Exception.Message)`n"
    }

    Start-Sleep -Milliseconds 500
}
