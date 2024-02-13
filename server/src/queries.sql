-- name: get_pb_split_times
-- Get fastest split times for a given player on a given trail
SELECT
    MIN(SplitTime.checkpoint_time) AS min_checkpoint_time,
    SplitTime.checkpoint_num
FROM
    SplitTime
    INNER JOIN Time ON SplitTime.time_id = Time.time_id
    INNER JOIN Player ON Time.steam_id = Player.steam_id
WHERE
    Time.trail_name = :trail_name
    AND Time.ignored = 0 
    AND Time.verified = 1
    AND SplitTime.time_id = (
        SELECT
            SplitTime.time_id
        FROM
            SplitTime
            INNER JOIN Time ON SplitTime.time_id = Time.time_id
            INNER JOIN Player ON Time.steam_id = Player.steam_id
        WHERE
            Time.trail_name = :trail_name
            AND Time.ignored = 0 
            AND Time.verified = 1
            AND Time.steam_id = :steam_id
        ORDER BY
            SplitTime.checkpoint_num DESC, SplitTime.checkpoint_time ASC
        LIMIT 1
    )
GROUP BY
    SplitTime.checkpoint_num
ORDER BY
    SplitTime.checkpoint_num ASC;

-- name: get_wr_split_times
-- Get fastest split times for a given trail
SELECT
    MIN(SplitTime.checkpoint_time) AS min_checkpoint_time,
    SplitTime.checkpoint_num
FROM
    SplitTime
    INNER JOIN Time ON SplitTime.time_id = Time.time_id
    INNER JOIN Player ON Time.steam_id = Player.steam_id
WHERE
    Time.trail_name = :trail_name
    AND Time.ignored = 0 
    AND Time.verified = 1
    AND SplitTime.time_id = (
        SELECT
            SplitTime.time_id
        FROM
            SplitTime
            INNER JOIN Time ON SplitTime.time_id = Time.time_id
            INNER JOIN Player ON Time.steam_id = Player.steam_id
        WHERE
            Time.trail_name = :trail_name
            AND Time.ignored = 0 
            AND Time.verified = 1
        ORDER BY
            SplitTime.checkpoint_num DESC, SplitTime.checkpoint_time ASC
        LIMIT 1
    )
GROUP BY
    SplitTime.checkpoint_num
ORDER BY
    SplitTime.checkpoint_num ASC;

-- name: update_player
-- Update the player's name and avatar
REPLACE INTO Player (
    steam_id,
    steam_name,
    avatar_src
)
VALUES (
    :steam_id, :steam_name, :avatar_src
)

-- name: get_replay_name^
-- Get the replay name associated with a given time.
SELECT ('replay_' || Time.time_id || '_' || Player.steam_name || '.replay') AS value
FROM Time
INNER JOIN Player ON Time.steam_id = Player.steam_id
WHERE time_id = :time_id

-- name: player_id_from_name^
-- Get the player id from the player name.
SELECT Player.steam_id AS value
FROM Player
WHERE steam_name = :steam_name

-- name: player_name_from_id^
-- Get the 
SELECT steam_name AS value
FROM Player
WHERE steam_id = :steam_id


-- name: get_authenticated_discord_ids
-- Get the valid Discord IDs.
SELECT
    discord_id
FROM
    User
WHERE
    valid = "TRUE"

-- name: get_discord_steam_connetion^
-- get steam ID associated with given discord id
SELECT steam_id AS value
FROM User
WHERE discord_id = :discord_id

-- name: get_time_details^
-- Get the time details for a given time id.
SELECT
    *
FROM
    all_times
WHERE
    all_times.time_id = :time_id

-- name: get_all_times
-- Get all times for a given trail
SELECT * FROM all_times
LIMIT :limit

-- name: get_all_players
-- Get all players
SELECT Player.steam_id, Player.steam_name, Player.avatar_src, Rep.rep, max(Rep.timestamp) as rep_timestamp
FROM Player
INNER JOIN Rep on Rep.steam_id = Player.steam_id
GROUP BY Player.steam_id
ORDER BY Player.steam_name ASC

-- name: get_all_trails
-- Get all trails
SELECT * FROM TrailInfo

-- name: get_all_worlds
-- Get all worlds
SELECT world_name
FROM Time
GROUP BY world_name

-- name: get_leaderboard
-- Get the leaderboard for a given trail
SELECT
    starting_speed,
    steam_name,
    bike_type,
    MIN(checkpoint_time),
    Time.version,
    Time.verified,
    Time.time_id
FROM
    Time
    INNER JOIN
        SplitTime ON SplitTime.time_id = Time.time_id
    INNER JOIN
        (
            SELECT
                max(checkpoint_num) AS max_checkpoint
            FROM
                SplitTime
                INNER JOIN
                    Time ON Time.time_id = SplitTime.time_id
                WHERE LOWER(Time.trail_name) = LOWER(
                    :trail_name
                )
        ) ON SplitTime.time_id=Time.time_id
    INNER JOIN
        Player ON Player.steam_id = Time.steam_id
WHERE
    LOWER(trail_name) = LOWER(:trail_name)
    AND
    checkpoint_num = max_checkpoint
    AND
    Time.ignored = 0 AND Time.verified = 1
GROUP BY
    trail_name,
    Player.steam_id
ORDER BY
    checkpoint_time ASC
LIMIT :limit

-- name: get_player_avatar^
-- Get the player's avatar
SELECT avatar_src
FROM Player
WHERE steam_id = :steam_id

-- name: submit_discord_details
-- Submit the discord details
REPLACE INTO User
VALUES(
    :discord_id,
    "FALSE",
    :steam_id,
    :discord_name,
    :email
)

-- name: verify_time
-- Verify a time
UPDATE Time
SET verified = 1
WHERE time_id = :time_id

-- name: submit_time
-- Submit a time
INSERT INTO Time (
	steam_id, -- TEXT
	time_id, -- INTEGER NOT NULL UNIQUE
	timestamp, -- REAL
	world_name, -- TEXT
	trail_name, -- TEXT
    bike_type, -- TEXT
	starting_speed, -- REAL
	version, -- TEXT
	verified, -- INT NOT NULL
	ignored -- INT NOT NULL
)
VALUES (
	:steam_id, -- TEXT
	:time_id, -- INTEGER NOT NULL UNIQUE
	:timestamp, -- REAL
	:world_name, -- TEXT
	:trail_name, -- TEXT
    :bike_type, -- TEXT
	:starting_speed, -- REAL
	:version, -- TEXT
	:verified, -- INT NOT NULL
	:ignored -- INT NOT NULL
)

-- name: submit_split
-- Submit a split time
INSERT INTO
SplitTime (
    time_id,
    checkpoint_num,
    checkpoint_time
)
VALUES (
    :time_id,
    :checkpoint_num,
    :checkpoint_time
)