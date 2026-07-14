from fastapi.testclient import TestClient

from src.server import app

client = TestClient(app)


def teardown_function():
    client.post("/batch/stop")


def test_valid_start_returns_seq_zero():
    r = client.post("/batch/start", params={"points": 60, "refresh": 1.0, "reporting": 2})
    assert r.status_code == 200
    assert r.json() == {"seq": 0}


def test_reporting_out_of_range_rejected():
    assert client.post("/batch/start", params={"points": 60, "refresh": 1, "reporting": 0}).status_code == 400
    assert client.post("/batch/start", params={"points": 60, "refresh": 1, "reporting": 1001}).status_code == 400


def test_refresh_faster_than_reporting_rejected():
    # reporting=2 => min refresh 0.5s; 0.3s is faster than the data is produced.
    r = client.post("/batch/start", params={"points": 60, "refresh": 0.3, "reporting": 2})
    assert r.status_code == 400


def test_refresh_below_hard_floor_rejected():
    # reporting=100 => 1/reporting=0.01s, but the 0.25s floor still applies.
    r = client.post("/batch/start", params={"points": 60, "refresh": 0.1, "reporting": 100})
    assert r.status_code == 400


def test_points_below_batch_rejected():
    # reporting=10, refresh=1.0 => batch=10; window of 5 can't hold one batch.
    r = client.post("/batch/start", params={"points": 5, "refresh": 1.0, "reporting": 10})
    assert r.status_code == 400


def test_csv_cap_exceeded_rejected():
    # reporting=1000, refresh=30 => 30000 rows/CSV, over the 10000 cap.
    r = client.post("/batch/start", params={"points": 10000, "refresh": 30, "reporting": 1000})
    assert r.status_code == 400


def test_points_above_max_rejected():
    r = client.post("/batch/start", params={"points": 10001, "refresh": 1.0, "reporting": 2})
    assert r.status_code == 400
