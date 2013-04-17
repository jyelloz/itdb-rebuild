import mutagen
import gpod
import logging

_log = logging.getLogger(__name__)


def get_metadata(path):
    return mutagen.File(path), mutagen.File(path, easy=True)


def get_first(d, key, default=None):
    try:
        return d.get(key)[0].encode('utf-8')
    except:
        return default


def get_any_artwork(md_hard):

    try:
        return md_hard['covr'][0]
    except:
        pass

    try:
        return md_hard['APIC:'].data
    except:
        pass

    return None


def is_compilation(md_easy):

    try:
        compilation = bool(
            int(
                md_easy.get('compilation', [0])[0]
            )
        )

        if compilation:
            return True
    except:
        pass

    performer = md_easy.get('performer')
    albumartist = md_easy.get('albumartist')
    artist = md_easy.get('artist')

    if performer is not None and artist is not None:
        return performer[0] != artist[0]

    if albumartist is not None and artist is not None:
        return artist[0] != albumartist[0]

    try:
        album_type = get_first(md_easy, 'musicbrainz_albumtype')
        return album_type == u'soundtrack' or album_type == u'compilation'
    except:
        return False


def find_files(music_directory, action=None):
    from os import walk
    from os.path import join

    for root, dirs, files in walk(music_directory):

        file_paths = (join(root, f) for f in files)

        if action:
            for p in file_paths:
                action(p)


def rebuild(mountpoint, ipod_name, dry_run=True):

    db = gpod.itdb_new()
    gpod.itdb_set_mountpoint(db, mountpoint)

    master = gpod.itdb_playlist_new(ipod_name, False)
    gpod.itdb_playlist_set_mpl(master)
    gpod.itdb_playlist_add(db, master, -1)

    mb_albumid_to_artwork = dict()

    def store_artwork(artwork_data, mb_albumid):

        from gi.repository import Gio, GdkPixbuf

        artwork_in = Gio.MemoryInputStream.new_from_data(artwork_data)

        artwork_pixbuf = GdkPixbuf.Pixbuf.new_from_stream(
            artwork_in,
            None,
        )

        artwork = gpod.itdb_artwork_new()

        gpod.itdb_artwork_set_thumbnail_from_pixbuf(
            artwork,
            artwork_pixbuf,
            0,
            None,
        )

        mb_albumid_to_artwork[mb_albumid] = artwork

        return artwork

    def get_artwork(mb_albumid):
        return mb_albumid_to_artwork.get(mb_albumid)

    def action(path):

        from os import sep, stat
        from os.path import relpath

        from mutagen.m4a import M4AInfo

        relative_path = relpath(path, mountpoint)
        ipod_path = ':' + relative_path.replace(sep, ':')

        md_hard, md_easy = get_metadata(path)
        info = md_easy.info
        c = is_compilation(md_easy)

        track = gpod.itdb_track_new()

        track.title = get_first(md_easy, 'title')
        track.artist = get_first(md_easy, 'artist')
        track.album = get_first(md_easy, 'album')
        track.compilation = c
        track.tracklen = int(info.length * 1000)
        track.bitrate = int(info.bitrate)
        track.samplerate = int(info.sample_rate)
        track.ipod_path = ipod_path
        track.size = stat(path).st_size

        if isinstance(info, M4AInfo):
            track.filetype = 'M4A-file'
        else:
            track.filetype = 'MP3-file'

        mb_albumid = get_first(md_easy, 'musicbrainz_albumid', None)
        if mb_albumid is not None:

            existing_artwork = get_artwork(mb_albumid)
            if existing_artwork is not None:
                _log.debug(
                    'found existing artwork for track %r (%r-%r)',
                    path,
                    get_first(md_easy, 'artist'),
                    get_first(md_easy, 'album'),
                )
                artwork = existing_artwork
            else:
                artwork_data = get_any_artwork(md_hard)
                if artwork_data is not None:
                    _log.debug(
                        'storing artwork for track %r',
                        path,
                    )
                    artwork = store_artwork(artwork_data, mb_albumid)
                else:
                    artwork = None
        else:
            artwork = None

        if artwork is not None:
            track.artwork = gpod.itdb_artwork_duplicate(artwork)

        try:
            track_number = get_first(md_easy, 'tracknumber')
            disc_number = get_first(md_easy, 'discnumber', '1')

            track_n = track_number.split('/')
            disc_n = disc_number.split('/')

            track.track_nr = int(track_n[0])
            track.cd_nr = int(disc_n[0])

            if len(track_n) > 1:
                track.tracks = int(track_n[1])

            if len(disc_n) > 1:
                track.cds = int(disc_n[1])

        except Exception, e:
            _log.error('%r %r', e, md_easy)

        gpod.itdb_track_add(db, track, -1)
        gpod.itdb_playlist_add_track(master, track, -1)

    music_directory = gpod.itdb_get_music_dir(mountpoint)

    find_files(music_directory, action)

    if dry_run:
        _log.info('dry run, quitting')
        return

    _log.info('saving itunesdb')
    gpod.itdb_write(db, None)
    _log.info('done')


def main():

    from argparse import ArgumentParser

    logging.basicConfig(level=logging.DEBUG)

    parser = ArgumentParser()

    parser.add_argument(
        '-L',
        '--ipod-name',
        default='iPod',
    )

    parser.add_argument(
        '-n',
        '--dry-run',
        action='store_true',
    )

    parser.add_argument(
        'mountpoint'
    )

    args = parser.parse_args()
    rebuild(
        mountpoint=args.mountpoint,
        ipod_name=args.ipod_name,
        dry_run=args.dry_run
    )
