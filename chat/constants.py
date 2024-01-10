import json


DEALER_CHAT_SQL = """
    SELECT
    c.id,
    'Manager' as name,
    null AS image,
    (
        SELECT COUNT(m.id) FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        WHERE m.chat_id = c.id AND m.is_read = false AND mu.status != %s
    ) AS new_messages_count,
    (
        SELECT
            JSONB_BUILD_OBJECT(
                ('id')::text, m.id,
                ('sender')::text, 'Manager',
                ('chat_id')::text, m.chat_id,
                ('text')::text, m.text,
                ('is_read')::text, m.is_read,
                ('created_at')::text, m.created_at,
                ('attachments')::text,
                CASE WHEN COUNT(att.id) > 0 THEN 
                ARRAY_AGG(
                    JSONB_BUILD_OBJECT(
                        ('id')::text, att.id,
                        ('file')::text, CONCAT(%s, att.file)
                    )
                ) END
            )
        FROM chat_message AS m
        LEFT JOIN chat_messageattachment AS att ON att.message_id = m.id
        WHERE m.chat_id = c.id
        GROUP BY m.id
        ORDER BY m.created_at DESC
        LIMIT 1
    ) AS last_message
    FROM chat_chat AS c
    WHERE c.dealer_id = %s
    LIMIT 1
"""

CITY_CHATS_SQL = """
    SELECT
    c.id,
    cu.name AS name,
    cu.image AS image,
    (
        SELECT COUNT(m.id) FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        WHERE m.chat_id = c.id AND m.is_read = false AND mu.status != %s
    ) AS new_messages_count,
    (
        SELECT
            JSONB_BUILD_OBJECT(
                ('id')::text, m.id,
                ('sender')::text, mu.name,
                ('chat_id')::text, m.chat_id,
                ('text')::text, m.text,
                ('is_read')::text, m.is_read,
                ('created_at')::text, m.created_at,
                ('attachments')::text,
                CASE WHEN COUNT(att.id) > 0 THEN 
                ARRAY_AGG(
                    JSONB_BUILD_OBJECT(
                        ('id')::text, att.id,
                        ('file')::text, CONCAT(%s, att.file)
                    )
                ) END
            )
        FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        LEFT JOIN chat_messageattachment AS att ON att.message_id = m.id
        WHERE m.chat_id = c.id
        GROUP BY m.id, mu.id
        ORDER BY m.created_at DESC
        LIMIT 1
    ) AS last_message,
    (
        SELECT COUNT(*)
        FROM chat_message AS m
        WHERE m.chat_id = c.id
    ) AS total_messages_count,
    (
        SELECT m.created_at
        FROM chat_message AS m
        WHERE m.chat_id = c.id
        ORDER BY m.created_at DESC
        LIMIT 1
    ) AS last_message_created
    FROM chat_chat AS c
    JOIN account_myuser AS cu ON cu.id = c.dealer_id
    JOIN account_dealerprofile AS dp ON dp.user_id = cu.id
    WHERE dp.city_id = %s
    ORDER BY last_message_created DESC NULLS LAST, new_messages_count DESC, total_messages_count DESC
    LIMIT %s OFFSET %s
"""

CITY_SEARCH_CHATS_SQL = """
    SELECT
    c.id,
    cu.name AS name,
    cu.image AS image,
    (
        SELECT COUNT(m.id) FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        WHERE m.chat_id = c.id AND m.is_read = false AND mu.status != %s
    ) AS new_messages_count,
    (
        SELECT
            JSONB_BUILD_OBJECT(
                ('id')::text, m.id,
                ('sender')::text, mu.name,
                ('chat_id')::text, m.chat_id,
                ('text')::text, m.text,
                ('is_read')::text, m.is_read,
                ('created_at')::text, m.created_at,
                ('attachments')::text,
                CASE WHEN COUNT(att.id) > 0 THEN 
                ARRAY_AGG(
                    JSONB_BUILD_OBJECT(
                        ('id')::text, att.id,
                        ('file')::text, CONCAT(%s, att.file)
                    )
                ) END
            )
        FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        LEFT JOIN chat_messageattachment AS att ON att.message_id = m.id
        WHERE m.chat_id = c.id
        GROUP BY m.id, mu.id
        ORDER BY m.created_at DESC
        LIMIT 1
    ) AS last_message,
    (
        SELECT COUNT(*)
        FROM chat_message AS m
        WHERE m.chat_id = c.id
    ) AS total_messages_count,
    (
        SELECT m.created_at
        FROM chat_message AS m
        WHERE m.chat_id = c.id
        ORDER BY m.id ASC, m.created_at DESC
        LIMIT 1
    ) AS last_message_created
    FROM chat_chat AS c
    JOIN account_myuser AS cu ON cu.id = c.dealer_id
    JOIN account_dealerprofile AS dp ON dp.user_id = cu.id
    WHERE dp.city_id = %s AND cu.name ILIKE %s
    ORDER BY last_message_created DESC NULLS LAST, new_messages_count DESC, total_messages_count DESC
    LIMIT %s OFFSET %s
"""

MANAGER_CHATS_SQL = """
    SELECT
    c.id,
    cu.name AS name,
    cu.image AS image,
    (
        SELECT COUNT(m.id) FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        WHERE m.chat_id = c.id AND m.is_read = false AND mu.status != %s
    ) AS new_messages_count,
    (
        SELECT
            JSONB_BUILD_OBJECT(
                ('id')::text, m.id,
                ('sender')::text, mu.name,
                ('chat_id')::text, m.chat_id,
                ('text')::text, m.text,
                ('is_read')::text, m.is_read,
                ('created_at')::text, m.created_at,
                ('attachments')::text,
                CASE WHEN COUNT(att.id) > 0 THEN 
                ARRAY_AGG(
                    JSONB_BUILD_OBJECT(
                        ('id')::text, att.id,
                        ('file')::text, att.file
                    )
                ) END
            )
        FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        LEFT JOIN chat_messageattachment AS att ON att.message_id = m.id
        WHERE m.chat_id = c.id
        GROUP BY m.id, mu.id
        ORDER BY m.created_at DESC
        LIMIT 1
    ) AS last_message,
    (
        SELECT COUNT(*)
        FROM chat_message AS m
        WHERE m.chat_id = c.id
    ) AS total_messages_count,
    (
        SELECT m.created_at
        FROM chat_message AS m
        WHERE m.chat_id = c.id
        ORDER BY m.created_at DESC
        LIMIT 1
    ) AS last_message_created
    FROM chat_chat AS c
    JOIN account_myuser AS cu ON cu.id = c.dealer_id
    JOIN account_dealerprofile AS dp ON dp.user_id = cu.id
    JOIN account_dealerprofile_managers as dm ON dm.dealerprofile_id = dp.id
    WHERE dm.myuser_id = %s
    ORDER BY last_message_created DESC NULLS LAST, new_messages_count DESC, total_messages_count DESC
    LIMIT %s OFFSET %s
"""

MANAGER_CHATS_SEARCH_SQL = """
    SELECT
    c.id,
    cu.name AS name,
    cu.image AS image,
    (
        SELECT COUNT(m.id) FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        WHERE m.chat_id = c.id AND m.is_read = false AND mu.status != %s
    ) AS new_messages_count,
    (
        SELECT
            JSONB_BUILD_OBJECT(
                ('id')::text, m.id,
                ('sender')::text, mu.name,
                ('chat_id')::text, m.chat_id,
                ('text')::text, m.text,
                ('is_read')::text, m.is_read,
                ('created_at')::text, m.created_at,
                ('attachments')::text,
                CASE WHEN COUNT(att.id) > 0 THEN 
                ARRAY_AGG(
                    JSONB_BUILD_OBJECT(
                        ('id')::text, att.id,
                        ('file')::text, att.file
                    )
                ) END
            )
        FROM chat_message AS m
        JOIN account_myuser AS mu ON mu.id = m.sender_id
        LEFT JOIN chat_messageattachment AS att ON att.message_id = m.id
        WHERE m.chat_id = c.id
        GROUP BY m.id, mu.id
        ORDER BY m.created_at DESC
        LIMIT 1
    ) AS last_message,
    (
        SELECT COUNT(*)
        FROM chat_message AS m
        WHERE m.chat_id = c.id
    ) AS total_messages_count,
    (
        SELECT m.created_at
        FROM chat_message AS m
        WHERE m.chat_id = c.id
        ORDER BY m.created_at DESC
        LIMIT 1
    ) AS last_message_created
    FROM chat_chat AS c
    JOIN account_myuser AS cu ON cu.id = c.dealer_id
    JOIN account_dealerprofile AS dp ON dp.user_id = cu.id
    JOIN account_dealerprofile_managers as dm ON dm.dealerprofile_id = dp.id
    WHERE dm.myuser_id = %s AND cu.name ILIKE %s
    ORDER BY last_message_created DESC NULLS LAST, new_messages_count DESC, total_messages_count DESC
    LIMIT %s OFFSET %s
"""


CHATS_IGNORE_COLS = ("total_messages_count", "last_message_created")
CHAT_FIELDS_SUBSTITUTES = {
    "last_message": json.loads,
    "id": str
}
