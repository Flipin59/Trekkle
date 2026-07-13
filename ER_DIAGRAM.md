# ER Diagram

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string email
        string password_hash
        string full_name
        string phone
        string role
        string status
        datetime created_at
    }

    TREKS {
        int id PK
        string name
        string location
        string description
        string difficulty
        int duration_days
        int total_slots
        int available_slots
        date start_date
        date end_date
        string status
        string trek_updates
        datetime created_at
    }

    STAFF_ASSIGNMENT {
        int trek_id PK, FK
        int staff_assigned PK, FK
    }

    BOOKING {
        int id PK
        int user_id FK
        int trek_id FK
        datetime booking_date
        string status
    }

    USER ||--o{ BOOKING : makes
    TREKS ||--o{ BOOKING : has
    TREKS ||--o{ STAFF_ASSIGNMENT : assigned_staff
    USER ||--o{ STAFF_ASSIGNMENT : staff_member
```

## Notes

- `STAFF_ASSIGNMENT.staff_assigned` points to `USER.id` and is intended for users with the `staff` role.
- `BOOKING.status` follows the `Booked`, `Cancelled`, and `Completed` convention used in the model.
- `USER.status` follows the `active`, `pending`, and `blacklisted` convention used in the model.