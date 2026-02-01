# Understanding Optional Authentication Endpoints

## What is Optional Authentication?

Optional authentication means an endpoint works for **both authenticated and anonymous users**, but provides different responses or functionality based on authentication status.

Think of it like a physical store: anyone can walk in and browse (anonymous), but loyalty card members (authenticated) get special prices and personalized recommendations.

---

## Real-World Examples

### Example 1: Blog Posts List

**Without Optional Auth (Bad UX):**

```python
# Two separate endpoints - awkward!
@router.get("/posts")  # Public only
async def list_posts_public():
    return get_public_posts()

@router.get("/posts/personalized")  # Authenticated only
async def list_posts_personalized(user: User = Depends(get_current_user)):
    return get_user_posts(user)
```

**With Optional Auth (Good UX):**

```python
@router.get("/posts")
async def list_posts(user: Optional[User] = Depends(get_optional_user)):
    """List blog posts - personalized if logged in, public if not."""
    
    if user:
        # Authenticated: Show personalized feed
        return {
            "posts": get_personalized_posts(user),
            "following": get_following_posts(user),
            "recommended": get_ai_recommendations(user),
            "draft_count": count_user_drafts(user)
        }
    else:
        # Anonymous: Show trending posts
        return {
            "posts": get_trending_posts(),
            "featured": get_featured_posts()
        }
```

**Why This Matters:**

- ✅ One clean API endpoint
- ✅ Progressive enhancement (works for everyone, better for logged-in users)
- ✅ Better SEO (search engines can crawl public version)
- ✅ Simpler frontend code

---

### Example 2: Product Page (E-commerce)

```python
@router.get("/products/{product_id}")
async def get_product(
    product_id: int,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get product details - enhanced for logged-in users."""
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(404, "Product not found")
    
    response = {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "description": product.description,
        "images": product.images
    }
    
    if user:
        # Authenticated users get extra features
        response["in_wishlist"] = is_in_wishlist(user, product_id)
        response["user_rating"] = get_user_rating(user, product_id)
        response["personalized_price"] = calculate_loyalty_price(user, product)
        response["recommended_accessories"] = get_recommendations(user, product)
        response["purchase_history"] = user_purchased_before(user, product_id)
    else:
        # Anonymous users see standard info only
        response["login_message"] = "Log in to see personalized prices and recommendations"
    
    return response
```

**Response for Anonymous User:**

```json
{
  "id": 123,
  "name": "Wireless Mouse",
  "price": 29.99,
  "description": "Ergonomic wireless mouse...",
  "login_message": "Log in to see personalized prices..."
}
```

**Response for Authenticated User:**

```json
{
  "id": 123,
  "name": "Wireless Mouse",
  "price": 29.99,
  "personalized_price": 24.99,  // 👈 Loyalty discount
  "in_wishlist": true,           // 👈 User data
  "user_rating": 5,              // 👈 Their rating
  "recommended_accessories": [...],
  "purchase_history": "Last purchased: 2024-01-15"
}
```

---

### Example 3: Video Streaming Platform

```python
@router.get("/videos/{video_id}")
async def get_video(
    video_id: int,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get video details and streaming URL."""
    
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    # Everyone gets basic info
    response = {
        "id": video.id,
        "title": video.title,
        "thumbnail": video.thumbnail,
        "duration": video.duration,
        "views": video.view_count
    }
    
    if user:
        # Authenticated: Full quality + user features
        response["streaming_url"] = get_full_quality_url(video)
        response["watch_progress"] = get_user_progress(user, video_id)
        response["quality_options"] = ["360p", "720p", "1080p", "4K"]
        response["is_favorited"] = is_favorited(user, video_id)
        response["continue_watching"] = user.last_position.get(video_id)
    else:
        # Anonymous: Limited preview only
        response["streaming_url"] = get_preview_url(video)  # 30-second preview
        response["quality_options"] = ["360p"]
        response["message"] = "Sign up for full access"
    
    return response
```

---

### Example 4: API Rate Limiting

```python
@router.get("/search")
async def search(
    query: str,
    user: Optional[User] = Depends(get_optional_user)
):
    """Search API with different rate limits based on authentication."""
    
    if user:
        # Authenticated: Higher rate limit
        rate_limit = check_rate_limit(f"user:{user.id}", limit=100, window=60)
        if not rate_limit.allowed:
            raise HTTPException(429, "Rate limit: 100 requests/minute")
        
        # Access to premium search features
        results = advanced_search(query, user_preferences=user.preferences)
        return {
            "results": results,
            "total": len(results),
            "rate_limit": {"remaining": rate_limit.remaining, "limit": 100}
        }
    else:
        # Anonymous: Lower rate limit
        rate_limit = check_rate_limit(f"ip:{request.client.host}", limit=10, window=60)
        if not rate_limit.allowed:
            raise HTTPException(429, "Rate limit: 10 requests/minute (sign up for more)")
        
        # Basic search only
        results = basic_search(query, limit=10)
        return {
            "results": results[:10],
            "total": len(results),
            "rate_limit": {"remaining": rate_limit.remaining, "limit": 10},
            "message": "Sign up for advanced search and higher limits"
        }
```

---

### Example 5: Social Media Feed

```python
@router.get("/feed")
async def get_feed(
    user: Optional[User] = Depends(get_optional_user),
    skip: int = 0,
    limit: int = 20
):
    """Get content feed - personalized for logged-in users."""
    
    if user:
        # Authenticated: Personalized algorithmic feed
        posts = get_algorithmic_feed(
            user=user,
            skip=skip,
            limit=limit,
            include_following=True,
            include_recommendations=True
        )
        
        # Enhance with user-specific data
        for post in posts:
            post["liked_by_user"] = has_user_liked(user, post.id)
            post["saved_by_user"] = has_user_saved(user, post.id)
            post["mutual_friends_count"] = count_mutual_friends(user, post.author)
        
        return {
            "posts": posts,
            "personalized": True,
            "unread_notifications": count_notifications(user)
        }
    else:
        # Anonymous: Trending/popular content only
        posts = get_trending_feed(skip=skip, limit=limit)
        
        return {
            "posts": posts,
            "personalized": False,
            "message": "Sign up to see posts from people you follow"
        }
```

---

## When to Use Optional Auth

### ✅ Good Use Cases

1. **Content Discovery Endpoints**
   - Blog posts, articles, videos
   - Product listings
   - Search results
   - Public profiles

2. **Public Resources with User Enhancements**
   - Maps (with saved locations for auth users)
   - Recipes (with saved favorites)
   - News (with reading history)

3. **Freemium Features**
   - Limited access for anonymous
   - Full access for authenticated
   - Preview content for unauthenticated

4. **SEO-Critical Pages**
   - Need to be crawlable by search engines
   - But want to enhance for logged-in users

### ❌ When NOT to Use Optional Auth

1. **User-Specific Data**

   ```python
   # BAD: This should always require auth
   @router.get("/me/orders")
   async def get_my_orders(user: Optional[User] = Depends(get_optional_user)):
       if not user:
           raise HTTPException(401, "Authentication required")
       return user.orders
   
   # GOOD: Use required auth
   @router.get("/me/orders")
   async def get_my_orders(user: User = Depends(get_current_user)):
       return user.orders
   ```

2. **Write Operations**

   ```python
   # BAD: Don't use optional auth for mutations
   @router.post("/posts")
   async def create_post(user: Optional[User] = Depends(get_optional_user)):
       if not user:
           raise HTTPException(401)
       # ...
   
   # GOOD: Always require auth for writes
   @router.post("/posts")
   async def create_post(user: User = Depends(get_current_user)):
       # ...
   ```

3. **Admin/Protected Resources**

   ```python
   # NEVER use optional auth for admin endpoints
   @router.get("/admin/users")
   async def list_all_users(user: User = Depends(require_admin)):
       # ...
   ```

---

## Your SvelteKit Frontend Pattern

With optional auth, your frontend can be simpler:

```typescript
// src/routes/posts/+page.server.ts
export const load = async ({ fetch }) => {
  // This endpoint works whether user is logged in or not!
  const response = await fetch('/api/posts');
  const data = await response.json();
  
  return {
    posts: data.posts,
    personalized: data.personalized || false
  };
};
```

```svelte
<!-- src/routes/posts/+page.svelte -->
<script lang="ts">
  export let data;
</script>

<h1>Blog Posts</h1>

{#if data.personalized}
  <p class="badge">✨ Personalized for you</p>
{:else}
  <p class="cta">
    <a href="/login">Sign in</a> for personalized recommendations
  </p>
{/if}

{#each data.posts as post}
  <PostCard {post} />
{/each}
```

---

## Summary

**Optional Authentication** is for endpoints that should:

- ✅ Work for everyone (authenticated and anonymous)
- ✅ Provide enhanced features for authenticated users
- ✅ Be SEO-friendly (crawlable by search engines)
- ✅ Support progressive enhancement (better experience when logged in)

**Required Authentication** is for endpoints that:

- ✅ Access user-specific data
- ✅ Perform write operations
- ✅ Access protected resources
- ✅ Require specific permissions/roles

The `get_optional_user` dependency makes implementing the optional pattern clean and consistent across your API! 🎯
