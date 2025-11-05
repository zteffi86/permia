from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import piexif
import io
from datetime import datetime
from typing import Optional


class ExifExtractor:
    """Extract and validate EXIF metadata from images"""

    def extract(self, file_bytes: bytes) -> dict:
        """
        Extract EXIF data from image bytes

        Returns dict with:
        - has_exif: bool
        - gps_latitude: float | None
        - gps_longitude: float | None
        - datetime: datetime | None
        - camera_make: str | None
        - camera_model: str | None
        - raw: dict (all EXIF tags)
        """
        try:
            img = Image.open(io.BytesIO(file_bytes))
            exif_bytes = img.info.get("exif")

            if not exif_bytes:
                return {"has_exif": False}

            exif_dict = piexif.load(exif_bytes)

            result = {
                "has_exif": True,
                "gps_latitude": None,
                "gps_longitude": None,
                "datetime": None,
                "camera_make": None,
                "camera_model": None,
                "raw": {},
            }

            # Extract GPS
            if "GPS" in exif_dict and exif_dict["GPS"]:
                gps_data = exif_dict["GPS"]
                result["gps_latitude"] = self._get_decimal_coords(
                    gps_data.get(piexif.GPSIFD.GPSLatitude),
                    gps_data.get(piexif.GPSIFD.GPSLatitudeRef),
                )
                result["gps_longitude"] = self._get_decimal_coords(
                    gps_data.get(piexif.GPSIFD.GPSLongitude),
                    gps_data.get(piexif.GPSIFD.GPSLongitudeRef),
                )

            # Extract datetime
            if "Exif" in exif_dict and exif_dict["Exif"]:
                dt_original = exif_dict["Exif"].get(piexif.ExifIFD.DateTimeOriginal)
                if dt_original:
                    try:
                        dt_str = dt_original.decode("utf-8")
                        result["datetime"] = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
                    except:
                        pass

            # Extract camera info
            if "0th" in exif_dict and exif_dict["0th"]:
                make = exif_dict["0th"].get(piexif.ImageIFD.Make)
                model = exif_dict["0th"].get(piexif.ImageIFD.Model)
                if make:
                    result["camera_make"] = make.decode("utf-8") if isinstance(make, bytes) else make
                if model:
                    result["camera_model"] = model.decode("utf-8") if isinstance(model, bytes) else model

            # Store raw for audit
            result["raw"] = self._serialize_exif(exif_dict)

            return result

        except Exception as e:
            print(f"EXIF extraction failed: {e}")
            return {"has_exif": False, "error": str(e)}

    def _get_decimal_coords(self, coords, ref) -> Optional[float]:
        """Convert GPS coordinates to decimal degrees"""
        if not coords or not ref:
            return None

        try:
            degrees = coords[0][0] / coords[0][1]
            minutes = coords[1][0] / coords[1][1]
            seconds = coords[2][0] / coords[2][1]

            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

            if ref in [b"S", b"W", "S", "W"]:
                decimal = -decimal

            return decimal
        except:
            return None

    def _serialize_exif(self, exif_dict: dict) -> dict:
        """Convert EXIF dict to JSON-serializable format"""
        result = {}
        for ifd in exif_dict:
            if isinstance(exif_dict[ifd], dict):
                result[ifd] = {}
                for tag in exif_dict[ifd]:
                    value = exif_dict[ifd][tag]
                    if isinstance(value, bytes):
                        try:
                            result[ifd][tag] = value.decode("utf-8")
                        except:
                            result[ifd][tag] = str(value)
                    else:
                        result[ifd][tag] = str(value)
        return result


# Singleton
exif_extractor = ExifExtractor()
