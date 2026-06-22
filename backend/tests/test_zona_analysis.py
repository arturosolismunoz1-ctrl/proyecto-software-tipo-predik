from app.services.zona_analysis import calculate_commercial_concentration


class DummyDB:
    def execute(self, query):
        class Result:
            def scalars(self):
                class ScalarResult:
                    def all(self):
                        return []
                return ScalarResult()
        return Result()


def test_calculate_commercial_concentration_no_rows():
    db = DummyDB()
    try:
        calculate_commercial_concentration(
            db,
            "org",
            {"type": "Polygon", "coordinates": [[[0, 0], [0,1], [1,1], [1,0], [0,0]]]},
            None,
        )
    except ValueError as exc:
        assert str(exc) == "ZONA_SIN_COBERTURA"
