import mutagen
import gpod
import logging

_log = logging.getLogger(__name__)


def get_metadata(path):
    return mutagen.File(path, easy=True)


def is_compilation(md):

    _log.debug('%r', md)

    """
    try:
        compilation = bool(
            int(
                md.get('compilation')
            )
        )

        if compilation:
            return True
    except:
        pass

    performer = md.get('performer')
    albumartist = md.get('albumartist')
    artist = md.get('artist')

    if performer is not None and artist is not None:
        return performer[0] != artist[0]

    if albumartist is not None and artist is not None:
        return artist[0] != albumartist[0]
    """

    try:
        album_type = md.get('musicbrainz_albumtype')[0]
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

    compilation_albums = set()

    def get_first(d, key, default=None):
        try:
            return d.get(key)[0].encode('utf-8')
        except:
            return default

    def action(path):

        from os import sep, stat
        from os.path import relpath

        from mutagen.m4a import M4AInfo

        relative_path = relpath(path, mountpoint)
        ipod_path = ':' + relative_path.replace(sep, ':')

        md = get_metadata(path)
        info = md.info
        c = is_compilation(md)
        if c:
            compilation_albums.add(get_first(md, 'album'))

        track = gpod.itdb_track_new()

        track.title = get_first(md, 'title')
        track.artist = get_first(md, 'artist')
        track.album = get_first(md, 'album')
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

        try:
            track_number = get_first(md, 'tracknumber')
            disc_number = get_first(md, 'discnumber', '1')

            track_n = track_number.split('/')
            disc_n = disc_number.split('/')

            track.track_nr = int(track_n[0])
            track.cd_nr = int(disc_n[0])

            if len(track_n) > 1:
                track.tracks = int(track_n[1])

            if len(disc_n) > 1:
                track.cds = int(disc_n[1])

        except Exception, e:
            _log.error('%r %r', e, md)

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

    logging.basicConfig(level=logging.INFO)

    parser = ArgumentParser()

    parser.add_argument(
        '-L',
        '--ipod-name',
        default='Joes iPod',
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
