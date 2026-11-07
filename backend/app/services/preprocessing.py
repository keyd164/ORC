"""Preserve original; warp only a large, convex, four-corner receipt."""
from PIL import Image, ImageOps
import numpy as np
import cv2


def preprocess(source, target):
    with Image.open(source) as im:
        rgb = np.array(ImageOps.exif_transpose(im).convert('RGB'))
    height, width = rgb.shape[:2]
    scale = min(1, 1400 / max(height, width))
    small = cv2.resize(rgb, None, fx=scale, fy=scale)
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    warped = False
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
        approx = cv2.approxPolyDP(contour, .02 * cv2.arcLength(contour, True), True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue
        if cv2.contourArea(approx) < .35 * small.shape[0] * small.shape[1]:
            continue
        points = approx.reshape(4, 2).astype('float32') / scale
        total = points.sum(axis=1)
        diff = np.diff(points, axis=1).ravel()
        ordered = np.array([points[total.argmin()], points[diff.argmin()],
                            points[total.argmax()], points[diff.argmax()]])
        if len(np.unique(ordered, axis=0)) != 4:
            continue
        tl, tr, br, bl = ordered
        w = int(max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl)))
        h = int(max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr)))
        if min(w, h) < 150 or max(w, h) / min(w, h) > 10:
            continue
        destination = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype='float32')
        rgb = cv2.warpPerspective(rgb, cv2.getPerspectiveTransform(ordered, destination), (w, h))
        warped = True
        break
    # Mild contrast only; never threshold away faint thermal text.
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    lab[:, :, 0] = cv2.createCLAHE(clipLimit=1.3, tileGridSize=(8, 8)).apply(lab[:, :, 0])
    Image.fromarray(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)).save(target)
    return {'perspective_corrected': warped, 'enhancement': 'mild_clahe'}
