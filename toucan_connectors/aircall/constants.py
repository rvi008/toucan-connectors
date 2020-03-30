"""File containing constants for AirCall connector"""

COLUMN_DICTIONARY = {
    'calls' : [
        'id',
        'direction',
        'duration',
        'answered_at',
        'ended_at',
        'raw_digits',
        'user_id',
        'tags',
        'user_name',
        'team',
        'day'
    ],
    'tags' : [
        'id',
        'name',
        'color',
        'description'
    ],
    'users': [
        'team',
        'user_id',
        'user_name',
        'user_created_at'
    ]
}

FILTER_DICTIONARY = {
    'calls' : """
        .results
        | map({calls}
        | .calls
        | map({
            id,
            direction,
            duration,
            answered_at,
            ended_at,
            raw_digits,
            user_id:.user.id,
            tags : .tags | map({name}),
            user_name:.user.name,
        }))
        | flatten
    """,
    'tags' : """
        [
            .results []
            | .tags[]
        ]
    """,
    'teams' : """
        .results []
        | [
            .teams[]
            | .name as $team
            | .users[]
            | {
                team: $team,
                user_id: .id,
                user_name: .name,
                user_created_at: .created_at
        }]
    """,
    'users' : """
        [
            .results []
            |  .users []
            | {
                user_id : .id,
                user_name:.name,
                user_created_at: .created_at
            }]
    """
}

# MAX_RUNS = 60
MAX_RUNS = 10
PER_PAGE = 50
