# Catbox Async Uploader

Catbox Async Uploader is a simple Python class to upload files and URLs to [Catbox.moe](https://catbox.moe), including its temporary storage feature, **Litterbox**, and album management.


## Usage

### Using Userhash

CatboxUploader supports using a **userhash** directly. You can pass the `userhash` when initializing the `CatboxUploader` and use it for authenticated uploads and album management.

### Initialize with Userhash

```python
from catbox_async_uploader.core import CatboxAsyncUploader

uploader = CatboxAsyncUploader(userhash="your_userhash_here")
```

### Initialize without Userhash

```python
from catbox_async_uploader.core import CatboxAsyncUploader

uploader = CatboxAsyncUploader()
```

### Upload a File

```python
link = await uploader.upload_file("path/to/your/file.jpg")
print(f"Uploaded file: {link}")
```

### Upload a Bytes

```python
async with aiofiles.open("test_content/image_2.jpg", "rb") as f:
    file_bytes = await f.read()
link = await uploader.upload_file(file_bytes, file_name="image_2.jpg")
print(f"Uploaded file: {link}")
```

### Upload a File to Litterbox (Temporary Storage)

Litterbox allows you to upload files for a temporary period, after which the files will be deleted automatically. Use the `upload_to_litterbox` method to upload files with a specified expiration time.

**Available expiration times**:
- `LitterboxDuration.H1`: 1 hour
- `LitterboxDuration.H12`: 12 hours
- `LitterboxDuration.H24`: 24 hours
- `LitterboxDuration.H72`: 3 days
- `LitterboxDuration.W1`: 1 week

```python
from catbox_async_uploader.enums import LitterboxDuration

link = uploader.upload_to_litterbox("path/to/your/file.jpg", duration=LitterboxDuration.H24)
print(f'Uploaded file (available for 24 hours): {link}')
```

### Create and Manage Albums

#### Create an Album

You can create an album with uploaded files, a title, and a description using the `create_album` method:

```python
album_link = await uploader.create_album(file_links, "My Album", "This is a test album")
print(f"Album created: {album_link}")
```

#### Edit an Album

You can edit an album by changing its title, description, or the files it contains:

```python
album_shortcode = uploader.get_shortcode_from_url(album_link)
await uploader.edit_album(album_shortcode, file_links, "Updated Album Title", "Updated description")
```

#### Delete an Album

You can delete an album by its shortcode:

```python
album_shortcode = uploader.get_shortcode_from_url(album_link)
await uploader.delete_album(album_shortcode)
```