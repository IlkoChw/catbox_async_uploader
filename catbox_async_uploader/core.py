import asyncio
import logging

import aiofiles
import aiohttp

from .enums import LitterboxDuration
from .exceptions import CatboxError, CatboxTimeoutError, CatboxConnectionError, CatboxHTTPError


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

FilePathOrBytes = str | bytes


class CatboxAsyncUploader:
    api_url: str = f"https://catbox.moe/user/api.php"
    file_url: str = "https://files.catbox.moe"
    album_url: str = "https://catbox.moe/c"
    default_timeout: int = 30
    default_album_chunk_size: int = 50
    default_album_time_sleep: float = 1.5

    def __init__(self, userhash: str = None):
        """
        Initialize CatboxAsyncUploader with optional userhash (similar to API key)
        :param userhash: A string containing the userhash for authenticated uploads and album management
        """
        self.userhash = userhash  # get your userhash here: https://catbox.moe/user/manage.php

    def _check_userhash_value(self) -> None:
        if self.userhash is None:
            raise CatboxError(f"Userhash is required.")

    @staticmethod
    async def _get_content(file_path_or_bytes: FilePathOrBytes) -> FilePathOrBytes:
        if isinstance(file_path_or_bytes, str):
            async with aiofiles.open(file_path_or_bytes, "rb") as f:
                return await f.read()
        elif isinstance(file_path_or_bytes, bytes):
            return file_path_or_bytes
        else:
            raise CatboxError("Only file paths are supported in this version.")

    @staticmethod
    def _prepare_content(
            file_path_or_bytes: FilePathOrBytes,
            file_name: str = None
    ) -> tuple[str, FilePathOrBytes]:
        content = file_path_or_bytes
        if file_name is None:
            if isinstance(file_path_or_bytes, str):
                file_name = file_path_or_bytes.replace("\\", "/").split("/")[-1]
            elif isinstance(file_path_or_bytes, bytes):
                raise CatboxError("Need to set file_name")
        return file_name, content

    def get_shortcode_from_url(self, url: str) -> str:
        if url.startswith(self.file_url) or url.startswith(self.album_url):
            url = url.split("/")[-1]
        return url

    async def upload_file(
            self,
            file_path_or_bytes: FilePathOrBytes,
            timeout: int = default_timeout,
            file_name: str = None,
    ) -> str:
        """
        Upload file to Catbox. Supports both file paths and BytesIO objects
        :param file_path_or_bytes: Path to the file to upload or a BytesIO object
        :param file_name: Name of the file with extension (e.g., file.png)
        :param timeout: Timeout in seconds for the upload request
        :return: URL of the uploaded file on Catbox
        """
        try:
            self._check_userhash_value()
            file_name, content = self._prepare_content(file_path_or_bytes, file_name=file_name)
            form_data = aiohttp.FormData()
            form_data.add_field("reqtype", "fileupload")
            form_data.add_field("userhash", self.userhash)
            form_data.add_field(
                "fileToUpload",
                await self._get_content(content),
                filename=file_name,
                content_type="application/octet-stream",
            )

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.post(self.api_url, data=form_data) as response:
                    if response.status != 200:
                        raise CatboxError("Failed to upload file to Catbox.")
                    response_text = await response.text()
                    response_text = response_text.strip()
                    logging.debug(f"file link: {response_text}")
                    return response_text

        except asyncio.TimeoutError:
            raise CatboxTimeoutError(f"Upload request timed out after {timeout} seconds.")
        except aiohttp.ClientConnectionError:
            raise CatboxConnectionError("Failed to connect to Catbox.")
        except aiohttp.ClientError as err:
            raise CatboxError(f"An error occurred: {err}")

    async def upload_to_litterbox(
            self,
            file_path_or_bytes: FilePathOrBytes,
            file_name=None,
            duration: LitterboxDuration = LitterboxDuration.H1,
            timeout=default_timeout
    ) -> str:
        """
        Upload file to Litterbox (temporary storage). Supports both file paths and BytesIO objects
        :param file_path_or_bytes: Path to the file to upload or a BytesIO object
        :param file_name: Name of the file with extension (e.g., file.png)
        :param duration: Duration for which the file will be available
        :param timeout: Timeout in seconds for the upload request
        :return: URL of the uploaded file on Litterbox.
        """
        try:
            form_data = aiohttp.FormData()
            form_data.add_field("reqtype", "fileupload")
            form_data.add_field("time", duration.value)
            form_data.add_field(
                "fileToUpload",
                await self._get_content(file_path_or_bytes),
                filename=file_name,
                content_type="application/octet-stream",
            )

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.post(self.api_url, data=form_data) as response:
                    if response.status != 200:
                        raise Exception("Failed to upload file to Catbox.")
                    response_text = await response.text()
                    response_text = response_text.strip()
                    logging.debug(f"litterbox file link: {response_text}")
                    return response_text.strip()

        except asyncio.TimeoutError:
            raise CatboxTimeoutError(f"Upload to Litterbox timed out after {timeout} seconds.")
        except aiohttp.ClientConnectionError:
            raise CatboxConnectionError("Failed to connect to Litterbox. The server might be down.")
        except aiohttp.ClientResponseError as err:
            raise CatboxHTTPError(f"HTTP error occurred: {err}")
        except aiohttp.ClientError as err:
            raise CatboxError(f"An error occurred: {err}")

    async def upload_album(
            self,
            file_paths: list[str],
            timeout: int = default_timeout,
            chunk_size: int = default_album_chunk_size,
            time_sleep: float = default_album_time_sleep,
    ) -> list[str]:
        """
        Upload multiple files as an album to Catbox and return their links. Supports both file paths
        objects
        :param file_paths: List of file paths
        :param timeout: Timeout in seconds for the upload request
        :param chunk_size: The number of files to upload in each chunk to avoid overwhelming the server
        :param time_sleep: The time in seconds to sleep between uploading chunks to avoid rate limiting
        :return: List of URLs of the uploaded files on Catbox
        """
        logging.debug("Start upload album")
        uploaded_links = []
        try:
            chunks = [
                file_paths[i:i + chunk_size]
                for i in range(0, len(file_paths), chunk_size)
            ]
            for index, chunk in enumerate(chunks, start=1):
                logging.debug(f"process chunk: {index}/{len(chunks)}")
                tasks = [
                    self.upload_file(file_path, timeout=timeout)
                    for file_path in chunk
                ]
                uploaded_links.extend(
                    await asyncio.gather(*tasks)
                )
                await asyncio.sleep(time_sleep)
            logging.debug("End upload album")
            return uploaded_links
        except asyncio.TimeoutError:
            raise CatboxTimeoutError(f"Album upload timed out after {timeout} seconds.")
        except aiohttp.ClientConnectionError:
            raise CatboxConnectionError("Failed to connect to Catbox. The server might be down.")
        except aiohttp.ClientResponseError as err:
            raise CatboxHTTPError(f"HTTP error occurred: {err}")
        except aiohttp.ClientError as err:
            raise CatboxError(f"An error occurred: {err}")

    async def upload_album_to_litterbox(
            self,
            file_paths: list[str],
            timeout: int = default_timeout,
            duration: LitterboxDuration = LitterboxDuration.H1,
            chunk_size: int = default_album_chunk_size,
            time_sleep: float = default_album_time_sleep,
    ) -> list[str]:
        """
        Upload multiple files as an album to litterbox and return their links. Supports both file paths
        objects
        :param file_paths: List of file paths
        :param timeout: Timeout in seconds for the upload request
        :param duration: Duration for which the file will be available
        :param chunk_size: The number of files to upload in each chunk to avoid overwhelming the server
        :param time_sleep: The time in seconds to sleep between uploading chunks to avoid rate limiting
        :return: List of URLs of the uploaded files on Catbox
        """
        try:
            chunks = [
                file_paths[i:i + chunk_size]
                for i in range(0, len(file_paths), chunk_size)
            ]
            logging.debug("Start upload album to litterbox")
            uploaded_links = []
            for index, chunk in enumerate(chunks, start=1):
                logging.debug(f"process chunk: {index}/{len(chunks)}")
                tasks = [
                    self.upload_to_litterbox(
                        file_path,
                        timeout=timeout,
                        duration=duration,
                    )
                    for file_path in chunk
                ]
                uploaded_links.extend(await asyncio.gather(*tasks))
                await asyncio.sleep(time_sleep)
            logging.debug("End upload album to litterbox")
            return uploaded_links
        except asyncio.TimeoutError:
            raise CatboxTimeoutError(f"Album upload timed out after {timeout} seconds.")
        except aiohttp.ClientConnectionError:
            raise CatboxConnectionError("Failed to connect to Catbox. The server might be down.")
        except aiohttp.ClientResponseError as err:
            raise CatboxHTTPError(f"HTTP error occurred: {err}")
        except aiohttp.ClientError as err:
            raise CatboxError(f"An error occurred: {err}")

    async def delete_files(self, files: list[str], timeout: int = default_timeout) -> None:
        """
        Delete multiple files from Catbox using userhash
        :param files: List of filenames to delete from Catbox
        :param timeout: The timeout in seconds to process a request
        """
        try:
            self._check_userhash_value()
            fields = [
                ("reqtype", "deletefiles"),
                ("userhash", self.userhash),
                ("files", " ".join(files)),
            ]
            form_data = aiohttp.FormData()
            form_data.add_fields(*fields)

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.post(self.api_url, data=form_data) as response:
                    response.raise_for_status()
                    print(f"Deleted files: {files}")
        except aiohttp.ClientError as err:
            raise CatboxError(f"Failed to delete files: {err}")

    async def create_album(self, files: list[str], title: str, description: str = "") -> str:
        """
        Create a new album on Catbox with the specified files
        :param files: List of filenames that have been uploaded to Catbox
        :param title: Title of the album
        :param description: Description of the album
        :return: Shortcode of the created album
        """
        try:
            self._check_userhash_value()
            fields = [
                ("reqtype", "createalbum"),
                ("userhash", self.userhash),
                ("title", title),
                ("desc", description),
                ("files", " ".join(" ".join([self.get_shortcode_from_url(url) for url in files]))),
            ]
            form_data = aiohttp.FormData()
            form_data.add_fields(*fields)

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, data=form_data) as response:
                    response.raise_for_status()
                    response_text = await response.text()
                    return response_text.strip()
        except aiohttp.ClientError as err:
            raise CatboxError(f"Failed to create album: {err}")

    async def edit_album(self, shortcode: str, files: list[str], title: str, description: str = "") -> None:
        """
        Edit an existing album on Catbox
        :param shortcode: The short alphanumeric code of the album
        :param files: List of filenames to be part of the album
        :param title: Title of the album
        :param description: Description of the album
        """
        try:
            self._check_userhash_value()
            fields = [
                ("reqtype", "editalbum"),
                ("userhash", self.userhash),
                ("short", shortcode),
                ("title", title),
                ("desc", description),
                ("files", " ".join([self.get_shortcode_from_url(url) for url in files])),
            ]
            form_data = aiohttp.FormData()
            form_data.add_fields(*fields)

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, data=form_data) as response:
                    response.raise_for_status()
        except aiohttp.ClientError as err:
            raise CatboxError(f"Failed to edit album: {err}")

    async def delete_album(self, shortcode: str) -> None:
        """
        Delete an album from Catbox
        :param shortcode: The short alphanumeric code of the album
        """
        try:
            self._check_userhash_value()
            fields = [
                ("reqtype", "deletealbum"),
                ("userhash", self.userhash),
                ("short", shortcode),
            ]
            form_data = aiohttp.FormData()
            form_data.add_fields(*fields)

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, data=form_data) as response:
                    response.raise_for_status()

        except aiohttp.ClientError as err:
            raise CatboxError(f"Failed to delete album: {err}")
