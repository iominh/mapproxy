# This file is part of the MapProxy project.
# Copyright (C) 2010 Omniscale <http://omniscale.de>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Retrieve tiles from different tile servers (TMS/TileCache/etc.).
"""

import sys
from mapproxy.image.opts import ImageOptions
from mapproxy.source import Source, SourceError
from mapproxy.client.http import HTTPClientError
from mapproxy.source import InvalidSourceQuery
from mapproxy.layer import BlankImage, map_extent_from_grid
from mapproxy.util import reraise_exception

import logging
log = logging.getLogger('mapproxy.source.tile')
log_config = logging.getLogger('mapproxy.config')
class TiledSource(Source):
    def __init__(self, grid, client, inverse=False, coverage=None, image_opts=None):
        Source.__init__(self, image_opts=image_opts)
        self.grid = grid
        self.client = client
        self.inverse = inverse
        self.image_opts = image_opts or ImageOptions()
        self.coverage = coverage
        self.extent = coverage.extent if coverage else map_extent_from_grid(grid)
    
    def get_map(self, query):
        if self.grid.tile_size != query.size:
            ex = InvalidSourceQuery(
                'tile size of cache and tile source do not match: %s != %s'
                 % (self.grid.tile_size, query.size)
            )
            log_config.error(ex)
            raise ex
            
        if self.grid.srs != query.srs:
            ex = InvalidSourceQuery(
                'SRS of cache and tile source do not match: %r != %r'
                % (self.grid.srs, query.srs)
            )
            log_config.error(ex)
            raise ex

        if self.coverage and not self.coverage.intersects(query.bbox, query.srs):
            raise BlankImage()
        
        _bbox, grid, tiles = self.grid.get_affected_tiles(query.bbox, query.size)
        
        if grid != (1, 1):
            raise InvalidSourceQuery('BBOX does not align to tile')

        tile_coord = tiles.next()
        
        if self.inverse:
            tile_coord = self.grid.flip_tile_coord(tile_coord)
        try:
            return self.client.get_tile(tile_coord, format=query.format)
        except HTTPClientError, e:
            log.warn('could not retrieve tile: %s', e)
            reraise_exception(SourceError(e.args[0]), sys.exc_info())