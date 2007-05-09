# -*- coding: UTF-8 -*-
# Copyright (C) 2005 Piotr Macuk <piotr@macuk.pl>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# Import from the future
from __future__ import absolute_import

# Import from the Standard Library
import mimetypes

# Import from itools
from .csv import parse, CSV, Row, IntegerKey
from .parser import parse


__all__ = [
    # Functions
    'parse',
    # Classes
    'CSV',
    'Row']



mimetypes.add_type('text/comma-separated-values', '.csv')
