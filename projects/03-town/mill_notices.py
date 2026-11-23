"""Print the original county notices on one shared 1024 px sheet."""
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFont

def print_notices():
    rng = random.Random(187)
    sheet = Image.new("RGB", (1024, 1024))
    for i, (head, rows) in enumerate((
        ("COUNTY ORDER 17", ("AREA CLOSED", "BY ORDER OF THE COUNTY", "HALDEN RIDGE  /  WORKS DIVISION")),
        ("MISSING", ("ELIAN VALE", "LAST SEEN  12 FEB 1994", "COUNTY FILE   071")),
        ("MISSING", ("ELIAN VALE", "LAST SEEN  18 OCT 1994", "COUNTY FILE   071")),
        ("MILL WORKERS SERVICE", ("OUTBOUND     05:40    13:40", "RETURN           14:10    22:10", "FINAL SERVICE    31 OCT 1995")),
        ("NORTH RECEIVING", ("KEEP TO THE LINE", "AWAIT THE SECOND TONE", "GATE   4")),
        ("TIME OFFICE", ("VISITORS REGISTER HERE", "PASSENGERS MUST REMAIN SEATED", "SHIFT B      /      WINDOW 2")),
        ("HAULAGE", ("HALDEN MILLS", "WEAVING  /  STORES", "FLEET  08")),
        ("RECEIVING", ("DOCK  04", "NO UNSCHEDULED LOADS", "NORTH WORKS")),
    )):
        card=Image.new("RGB",(512,256),(185,174,144))
        d=ImageDraw.Draw(card)
        ink=(38,45,40)
        d.rectangle((7,7,504,249),outline=ink,width=3)
        d.rectangle((9,9,502,61),fill=(49,57,50))
        def line(x,y,value,size,colour):
            d.text((x,y),value,font=ImageFont.load_default(size=size),fill=colour)
        line(20,12,head,38,(218,211,185))
        x=22
        if i in (1,2):
            d.rectangle((17,72,143,230),fill=(138,134,113))
            d.polygon([(20,227),(39,193),(71,178),(68,162),(51,141),(48,105),(62,84),(90,82),
                       (109,98),(114,129),(104,153),(92,166),(93,180),(123,198),(139,228)],fill=(66,65,58))
            d.polygon([(59,109),(90,100),(105,115),(99,144),(85,161),(73,154),(62,137)],fill=(153,146,123))
            d.line([(61,122),(72,120),(77,123),(89,119),(99,120)],fill=ink,width=4)
            d.line([(80,124),(77,138),(83,138)],fill=ink,width=2)
            d.line((76,146,91,144),fill=ink,width=2)
            x=157
        for j,row in enumerate(rows):
            size=min(48 if j==0 else 30, int((488-x)/(len(row)*0.62)))
            line(x,77+j*54,row,size,ink)
        for _ in range(1700):
            xx,yy=rng.randrange(512),rng.randrange(256)
            d.line((xx,yy,xx+rng.randrange(1,5),yy), fill=rng.choice(((146,137,111),(174,162,134),(159,150,126))))
        sheet.paste(card,(i%2*512,i//2*256))
    sheet.save(Path(__file__).parent/"textures/decals/mill_notices.png")
if __name__=="__main__":
    print_notices()
