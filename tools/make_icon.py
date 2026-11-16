from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


root = Path(__file__).resolve().parents[1]
output = root / "resources"
output.mkdir(exist_ok=True)
size = 1024
image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((36, 36, size - 36, size - 36), radius=210, fill="#183d35")
draw.rounded_rectangle((78, 78, size - 78, size - 78), radius=176, outline="#6da698", width=12)
font_path = next((item for item in (
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
) if Path(item).exists()), None)
font = ImageFont.truetype(font_path, 420) if font_path else ImageFont.load_default()
text = "SP"
box = draw.textbbox((0, 0), text, font=font)
x = (size - (box[2] - box[0])) / 2 - box[0]
y = (size - (box[3] - box[1])) / 2 - box[1] - 34
draw.text((x, y), text, font=font, fill="#f3f0e7")
draw.rounded_rectangle((270, 736, 754, 766), radius=15, fill="#8bb9ad")
draw.rounded_rectangle((326, 806, 698, 828), radius=11, fill="#5f9488")
image.resize((256, 256), Image.Resampling.LANCZOS).save(output / "icon.png")
image.save(output / "icon.ico", sizes=[
    (16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)
])
