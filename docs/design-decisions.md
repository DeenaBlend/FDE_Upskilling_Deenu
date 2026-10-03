# Design Decisions - Milestone 2 Refactoring

## Summary

Refactored Milestone 1 codebase to follow SOLID principles and design patterns.

## Changes Made

### 1. Single Responsibility Principle

**Problem:** Fetchers had multiple responsibilities (fetch, transform, save)

**Solution:**
- Extracted `ArticleTransformer` class (responsibility: transform data)
- Extracted `MarkdownStorage` class (responsibility: save to files)
- Fetchers now only fetch (single responsibility), except GitHub Trending (see Trade-offs)

**Benefit:** Changes to transformation logic don't affect fetchers

### 2. Open/Closed Principle

**Problem:** Adding new source required modifying existing code

**Solution:**
- Created `BaseFetcher` abstract base class
- All fetchers inherit from BaseFetcher
- New sources extend without modifying existing

**Proof:** Added GitHub Trending with ZERO changes to existing code

**Benefit:** New sources can be added safely, no regression risk

### 3. Liskov Substitution Principle

**Problem:** Fetchers had inconsistent interfaces

**Solution:**
- Defined clear contract in BaseFetcher
- All fetchers implement same interface
- Substitutability tests ensure compliance

**Benefit:** Any fetcher can be used anywhere BaseFetcher is expected

### 4. Interface Segregation Principle

**Problem:** Risk of fat interfaces forcing unused methods

**Solution:**
- BaseFetcher has minimal interface (3 methods)
- Optional interfaces for special cases (AuthenticatedFetcher, etc.)
- Fetchers only implement what they need

**Benefit:** Clean, focused interfaces

### 5. Dependency Inversion Principle

**Problem:** Classes depended on concrete implementations

**Solution:**
- Created `ArticleStorage` interface
- Dependencies injected via constructors
- Code depends on abstractions

**Benefit:** Easy to test (inject mocks), easy to swap implementations

## Design Patterns Applied

### Factory Pattern

**Location:** `src/factories/fetcher_factory.py`

**Purpose:** Create fetchers without knowing concrete classes

**Usage:**
```python
fetcher = FetcherFactory.create('hackernews', transformer, storage)
```

**Benefit:** Configuration-driven fetcher creation

### Strategy Pattern

**Location:** `src/strategies/rate_limit_strategy.py`

**Purpose:** Swap rate limiting algorithms

**Usage:**
```python
fetcher = HackerNewsFetcher(
    transformer, storage,
    rate_limiter=TokenBucketStrategy(100, 60)
)
```

**Benefit:** Different strategies for different sources

### Template Method Pattern

**Location:** `src/fetchers/base_fetcher.py` (fetch_and_save method)

**Purpose:** Define algorithm skeleton, allow customization

**Benefit:** Consistent behavior across all fetchers

## Metrics

### Before Refactoring
- Classes: 6 (Article, HackerNewsFetcher, RSSFetcher, MarkdownStorage, RateLimiter, FetchOrchestrator)
- Responsibilities per class: ~3
- Extensibility: Requires modifying existing code
- Testability: Hard (concrete dependencies)

### After Refactoring
- Classes: 15 (Article, BaseFetcher + 3 fetchers, 2 optional fetcher interfaces, transformer, storage interface + MarkdownStorage, factory, 3 rate limit strategies, orchestrator)
- Responsibilities per class: 1
- Extensibility: Add new sources with zero existing code changes
- Testability: Easy (dependency injection, mocks)

## Trade-offs

### More Classes
- **Con:** More files to navigate
- **Pro:** Each class is simple and focused

### More Abstraction
- **Con:** Slightly more complex for beginners
- **Pro:** Much easier to maintain and extend

### Dependency Injection
- **Con:** More setup code
- **Pro:** Much easier to test

### GitHub Trending Parses Its Own Data
- **Con:** `GitHubTrendingFetcher` builds Articles itself instead of using `ArticleTransformer`, so it does more than fetch
- **Pro:** Adding it needed zero changes to `ArticleTransformer`, which keeps the Open/Closed proof clean

## Lessons Learned

1. **SRP makes code easier to change** - When file format needs to change, only touch MarkdownStorage and `Article.to_markdown()`, never the fetchers
2. **OCP proven by GitHub addition** - Added complete new source with zero risk
3. **DIP makes testing easy** - Can test orchestrator without real HTTP calls
4. **Design patterns solve real problems** - Not just theory, actually useful

## Next Steps

These patterns will be used in upcoming milestones:
- Milestone 3: Agents will use DIP
- Milestone 4: MCP servers will use Factory pattern
- Milestone 5: Evaluation will benefit from SRP

---

*Last updated: 2026-10-02*
*By: Deena Nath*