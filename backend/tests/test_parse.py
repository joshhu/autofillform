"""單元測試：座標解析。"""
from app.models.locate import parse_boxes, parse_point, parse_text_boxes


def test_parse_boxes_normalizes_to_pixels():
    boxes = parse_boxes("<box><0><0><500><1000></box>", w=200, h=100)
    assert len(boxes) == 1
    b = boxes[0]
    assert b.x1 == 0 and b.y1 == 0
    assert b.x2 == 100  # 500/1000*200
    assert b.y2 == 100  # 1000/1000*100


def test_parse_point():
    pt = parse_point("<box><500><250></box>", w=200, h=400)
    assert pt == (100.0, 100.0)


def test_parse_point_none_when_absent():
    assert parse_point("沒有座標", w=10, h=10) is None


def test_parse_text_boxes():
    ans = ("<ref>Email</ref><box><100><100><300><150></box>"
           "<ref>Name</ref><box><100><200><300><250></box>")
    texts = parse_text_boxes(ans, w=1000, h=1000)
    labels = {t.text for t in texts}
    assert "Email" in labels and "Name" in labels
    email = next(t for t in texts if t.text == "Email")
    assert email.bbox.x1 == 100 and email.bbox.y2 == 150


def test_bbox_center():
    boxes = parse_boxes("<box><0><0><1000><1000></box>", w=100, h=100)
    assert boxes[0].center == (50.0, 50.0)
