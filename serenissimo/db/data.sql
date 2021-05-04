INSERT
    OR IGNORE INTO ulss (id, name)
VALUES (1, 'Dolomiti'),
    (2, 'Marca Trevigiana'),
    (3, 'Serenissima'),
    (4, 'Veneto Orientale'),
    (5, 'Polesana'),
    (6, 'Euganea'),
    (7, 'Pedemontana'),
    (8, 'Berica'),
    (9, 'Scaligera');
INSERT
    OR IGNORE INTO status (id, update_interval)
VALUES (
        'unknown',
        (
            SELECT 60 * 60
        )
    ),
    (
        'eligible',
        (
            SELECT 60 * 60
        )
    ),
    (
        'maybe_eligible',
        (
            SELECT 60 * 60
        )
    ),
    (
        'not_eligible',
        (
            SELECT 6 * 60 * 60
        )
    ),
    (
        'not_registered',
        (
            SELECT 24 * 60 * 60
        )
    ),
    (
        'wrong_health_insurance_number',
        (
            SELECT 7 * 24 * 60 * 60
        )
    ),
    (
        'already_booked',
        (
            SELECT 7 * 24 * 60 * 60
        )
    ),
    (
        'already_vaccinated',
        (
            SELECT 7 * 24 * 60 * 60
        )
    );