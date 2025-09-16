def get_pagination(total_count: int, limit: int, offset: int) -> dict:
    
    return {
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_next": (offset + limit) < total_count,
        "has_previous": offset > 0
    }