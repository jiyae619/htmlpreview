# Blue LCD area in the last used outro frame, in output pixels. Usage: measure_lcd.py frame.png out_w
import sys, numpy as np
from PIL import Image
im = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(int)
H, W, _ = im.shape; k = int(sys.argv[2]) / W
blue = (im[..., 2] > 140) & (im[..., 0] < 140) & (im[..., 2] - im[..., 0] > 50)
ys, xs = np.where(blue)
x0, x1 = np.percentile(xs, [0.5, 99.5]); y0, y1 = np.percentile(ys, [0.5, 99.5])
print({'x': round(float(x0 * k), 1), 'y': round(float(y0 * k), 1), 'w': round(float((x1 - x0) * k), 1), 'h': round(float((y1 - y0) * k), 1)})
