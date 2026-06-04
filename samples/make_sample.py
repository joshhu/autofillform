"""產生一張簡單的測試表單截圖。"""
from PIL import Image, ImageDraw

W, H = 900, 640
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
d.text((40, 30), "Registration Form", fill="black")
fields = ["Full Name", "Email", "Phone", "Address"]
y = 90
for f in fields:
    d.text((60, y + 8), f, fill="black")
    d.rectangle([240, y, 760, y + 38], outline="gray", width=2)
    y += 80
d.rectangle([240, y, 420, y + 40], fill="#2563eb")
d.text((300, y + 12), "Submit", fill="white")
img.save("samples/form.png")
print("已產生 samples/form.png")
