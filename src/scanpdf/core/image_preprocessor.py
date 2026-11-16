import cv2
import numpy as np


def rotate_image(image, angle):
    normalized = int(angle) % 360
    height, width = image.shape[:2]
    if normalized == 90:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE), np.array(
            [[0, 1, 0], [-1, 0, width - 1], [0, 0, 1]], dtype=float)
    if normalized == 180:
        return cv2.rotate(image, cv2.ROTATE_180), np.array(
            [[-1, 0, width - 1], [0, -1, height - 1], [0, 0, 1]], dtype=float)
    if normalized == 270:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE), np.array(
            [[0, -1, height - 1], [1, 0, 0], [0, 0, 1]], dtype=float)
    return image, np.eye(3)


def estimate_skew(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    scale = min(1, 1600 / max(gray.shape))
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 1800, 70,
                            minLineLength=max(40, gray.shape[1] // 12), maxLineGap=15)
    if lines is None:
        return 0.0
    angles = []
    for line in lines[:, 0]:
        left, top, right, bottom = line
        angle = np.degrees(np.arctan2(bottom - top, right - left))
        if abs(angle) < 7:
            angles.append(angle)
    return float(np.median(angles)) if len(angles) >= 4 else 0.0


def preprocess(image, settings, rotation=0):
    output, transform = rotate_image(image, rotation)
    skew = estimate_skew(output) if settings.deskew else 0
    if abs(skew) >= 0.15:
        height, width = output.shape[:2]
        affine = cv2.getRotationMatrix2D((width / 2, height / 2), skew, 1)
        output = cv2.warpAffine(output, affine, (width, height),
                                borderValue=(255, 255, 255))
        transform = np.vstack([affine, [0, 0, 1]]) @ transform
    if settings.denoise:
        output = cv2.fastNlMeansDenoisingColored(output, None, 5, 5, 7, 21)
    if settings.contrast:
        lab = cv2.cvtColor(output, cv2.COLOR_RGB2LAB)
        lab[:, :, 0] = cv2.createCLAHE(2.0, (8, 8)).apply(lab[:, :, 0])
        output = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    if settings.binarize:
        gray = cv2.cvtColor(output, cv2.COLOR_RGB2GRAY)
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 35, 15)
        output = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    return output, transform, skew


def transform_box(box, matrix):
    points = np.column_stack([np.array(box, dtype=float), np.ones(len(box))])
    result = (np.asarray(matrix) @ points.T).T
    return (result[:, :2] / result[:, 2:3]).tolist()

