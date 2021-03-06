# -*- coding: utf-8 -*-
"""
ASDF for breqfast
    
:Copyright:
    Author: Lili Feng
    email: lfeng1011@gmail.com
"""
try:
    import surfpy.datarequest.browsebase as browsebase
except:
    import browsebase
import warnings
import obspy
from obspy.taup import TauPyModel
import smtplib
import numpy as np
from pyproj import Geod

geodist         = Geod(ellps='WGS84')
taupmodel       = TauPyModel(model="iasp91")

mondict = {1: 'JAN', 2: 'FEB', 3: 'MAR', 4: 'APR', 5: 'MAY', 6: 'JUN', 7: 'JUL', 8: 'AUG', 9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DEC'}


class breqfastASDF(browsebase.baseASDF):
    
    def request_noise(self, start_date = None, end_date = None, skipinv=True, chanrank=['LH', 'BH', 'HH'], channels='Z', label='LF',\
        quality = 'B', name = 'LiliFeng', email_address='lfengmac@gmail.com', iris_email='breq_fast@iris.washington.edu', verbose = True):
        """request continuous data for noise analysis
        """
        if start_date is None:
            start_date  = self.start_date
        else:
            start_date  = obspy.UTCDateTime(start_date)
        if end_date is None:
            end_date    = self.end_date
        else:
            end_date    = obspy.UTCDateTime(end_date)
        header_str1     = '.NAME %s\n' %name + '.INST CU\n'+'.MAIL University of Colorado Boulder\n'
        header_str1     += '.EMAIL %s\n' %email_address+'.PHONE\n'+'.FAX\n'+'.MEDIA: Electronic (FTP)\n'
        header_str1     += '.ALTERNATE MEDIA: Electronic (FTP)\n'
        FROM            = 'no_reply@surfpy.com'
        TO              = iris_email
        title           = 'Subject: Requesting Data\n\n'
        ctime           = start_date
        while(ctime <= end_date):
            year        = ctime.year
            month       = ctime.month
            day         = ctime.day
            ctime       += 86400
            year2       = ctime.year
            month2      = ctime.month
            day2        = ctime.day
            header_str2 = header_str1 +'.LABEL %s_%d.%s.%d\n' %(label, year, mondict[month], day)
            header_str2 += '.QUALITY %s\n' %quality +'.END\n'
            day_str     = '%d %d %d 0 0 0 %d %d %d 0 0 0' %(year, month, day, year2, month2, day2)
            out_str     = ''
            Nsta        = 0
            for network in self.inv:
                for station in network:
                    netcode = network.code
                    stacode = station.code
                    staid   = netcode+'.'+stacode
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        st_date     = station.start_date
                        ed_date     = station.end_date
                    if skipinv and (ctime < st_date or (ctime - 86400) > ed_date):
                        continue
                    # determine channel type
                    channel_type    = None
                    for chantype in chanrank:
                        tmpch       = station.select(channel = chantype+'?')
                        if len(tmpch) >= len(channels):
                            channel_type    = chantype
                            break
                    if channel_type is None:
                        if verbose:
                            print('!!! NO selected channel types: '+ staid)
                        continue
                    Nsta            += 1
                    for tmpch in channels:
                        chan        = channel_type + tmpch
                        chan_str    = '1 %s' %chan
                        sta_str     = '%s %s %s %s\n' %(stacode, netcode, day_str, chan_str)
                        out_str     += sta_str
            out_str     = header_str2 + out_str
            if Nsta == 0:
                print ('--- [NOISE DATA REQUEST] No data available in inventory, Date: %s' %(ctime - 86400).isoformat().split('T')[0])
                continue
            #========================
            # send email to IRIS
            #========================
            server  = smtplib.SMTP('localhost')
            MSG     = title + out_str
            server.sendmail(FROM, TO, MSG)
            server.quit()
            print ('--- [NOISE DATA REQUEST] email sent to IRIS, Date: %s' %(ctime - 86400).isoformat().split('T')[0])
        return
    
    def request_noise_obs(self, start_date = None, end_date = None, skipinv=True, chanrank=['L', 'B', 'H'],
            label='LF', quality = 'B', name = 'LiliFeng', obs_channels = ['H1', 'H2', 'HZ', 'DH'],
            send_email=False, email_address='lfengmac@gmail.com', iris_email='breq_fast@iris.washington.edu'):
        """request continuous obs data for noise analysis
        """
        #================================
        # Determine the channel type
        #================================
        is_obs_lst      = np.zeros(len(self.waveforms.list()), dtype = bool)
        chan_type_lst   = [] 
        ista            = 0
        for network in self.inv:
            for station in network:
                netcode = network.code
                stacode = station.code
                # use existence of pressure gauge to check if the station is obs or not
                tmpchanDH       = station.select(channel = '?DH')
                tmpEDH          = station.select(channel = 'EDH')
                if len(tmpchanDH) == 0:
                    is_obs      = False
                    tmpchanZ    = station.select(channel = '?HZ')
                elif len(tmpchanDH) == len(tmpEDH):
                    print ('--- [NOISE DATA REQUEST] EDH obs, only request Z component, station: %s.%s' %(netcode, stacode))
                    is_obs      = False
                    tmpchanZ    = station.select(channel = '?HZ')
                else:
                    is_obs          = True
                    is_obs_lst[ista]= True
                ista            += 1
                # determine the channel type
                chantype        = ''
                for tmpchtype in chanrank:
                    if is_obs:
                        tmpchanDH2  = tmpchanDH.select(channel = tmpchtype + 'DH')
                        if len(tmpchanDH2) > 0:
                            chantype= tmpchtype
                            break
                    else:
                        tmpchanZ2   = tmpchanZ.select(channel = tmpchtype + 'HZ')
                        if len(tmpchanZ2) > 0:
                            chantype= tmpchtype
                            break
                if chantype == '':
                    print ('--- [NOISE DATA REQUEST] No data available for station: %s.%s' %(netcode, stacode))
                    chan_type_lst.append('')
                    continue
                if is_obs:
                    # check if all channels exist
                    for tmpch in obs_channels:
                        try:
                            chan    = (station.select(channel = chantype+tmpch)).code
                        except:
                            print ('--- [NOISE DATA REQUEST] Not all obs channels available for station: %s.%s' %(netcode, stacode))
                            break 
                chan_type_lst.append(chantype)
        if not send_email:
            return chan_type_lst, is_obs_lst
        # initialization of date and header strings
        if start_date is None:
            start_date  = self.start_date
        else:
            start_date  = obspy.UTCDateTime(start_date)
        if end_date is None:
            end_date    = self.end_date
        else:
            end_date    = obspy.UTCDateTime(end_date)
        header_str1     = '.NAME %s\n' %name + '.INST CU\n'+'.MAIL University of Colorado Boulder\n'
        header_str1     += '.EMAIL %s\n' %email_address+'.PHONE\n'+'.FAX\n'+'.MEDIA: Electronic (FTP)\n'
        header_str1     += '.ALTERNATE MEDIA: Electronic (FTP)\n'
        FROM            = 'no_reply@surfpy.com'
        TO              = iris_email
        title           = 'Subject: Requesting Data\n\n'
        ctime           = start_date
        while(ctime <= end_date):
            year        = ctime.year
            month       = ctime.month
            day         = ctime.day
            ctime       += 86400
            year2       = ctime.year
            month2      = ctime.month
            day2        = ctime.day
            header_str2 = header_str1 +'.LABEL %s_%d.%s.%d\n' %(label, year, mondict[month], day)
            header_str2 += '.QUALITY %s\n' %quality +'.END\n'
            day_str     = '%d %d %d 0 0 0 %d %d %d 0 0 0' %(year, month, day, year2, month2, day2)
            out_str     = ''
            Nsta        = 0
            ista        = 0
            for network in self.inv:
                for station in network:
                    netcode = network.code
                    stacode = station.code
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        st_date     = station.start_date
                        ed_date     = station.end_date
                    if skipinv and (ctime < st_date or (ctime - 86400) > ed_date):
                        continue
                    chantype        = chan_type_lst[ista]
                    is_obs          = is_obs_lst[ista]
                    ista            += 1
                    if chantype == '':
                        continue 
                    if is_obs:
                        for tmpch in obs_channels:
                            chan        = chantype+tmpch
                            chan_str    = '1 %s' %chan
                            sta_str     = '%s %s %s %s\n' %(stacode, netcode, day_str, chan_str)
                            out_str     += sta_str
                    else:
                        chan        = chantype+'HZ'
                        chan_str    = '1 %s' %chan
                        sta_str     = '%s %s %s %s\n' %(stacode, netcode, day_str, chan_str)
                        out_str     += sta_str
                    Nsta    += 1
            out_str     = header_str2 + out_str
            if Nsta == 0:
                print ('--- [NOISE DATA REQUEST] No data available in inventory, Date: %s' %(ctime - 86400).isoformat().split('T')[0])
                continue
            #========================
            # send email to IRIS
            #========================
            server  = smtplib.SMTP('localhost')
            MSG     = title + out_str
            server.sendmail(FROM, TO, MSG)
            server.quit()
            print ('--- [NOISE DATA REQUEST] email sent to IRIS, Date: %s' %(ctime - 86400).isoformat().split('T')[0])
        return
    
    def request_rayleigh(self, lon0=None, lat0=None, minDelta=-1, maxDelta=181, chanrank=['LH', 'BH', 'HH'], channels='Z',\
            vmax=6.0, vmin=1.0, verbose=False, start_date=None, end_date=None, skipinv=True, label='LF', quality = 'B', name = 'LiliFeng',\
            email_address='lfengmac@gmail.com', iris_email='breq_fast@iris.washington.edu'):
        """request Rayleigh wave data from IRIS server
        ====================================================================================================================
        ::: input parameters :::
        lon0, lat0      - center of array. If specified, all waveform will have the same starttime and endtime
        min/maxDelta    - minimum/maximum epicentral distance, in degree
        channel         - Channel code, e.g. 'BHZ'.
                            Last character (i.e. component) can be a wildcard (‘?’ or ‘*’) to fetch Z, N and E component.
        vmin, vmax      - minimum/maximum velocity for surface wave window
        =====================================================================================================================
        """
        header_str1     = '.NAME %s\n' %name + '.INST CU\n'+'.MAIL University of Colorado Boulder\n'
        header_str1     += '.EMAIL %s\n' %email_address+'.PHONE\n'+'.FAX\n'+'.MEDIA: Electronic (FTP)\n'
        header_str1     += '.ALTERNATE MEDIA: Electronic (FTP)\n'
        FROM            = 'no_reply@surfpy.com'
        TO              = iris_email
        title           = 'Subject: Requesting Data\n\n'
        try:
            print (self.cat)
        except AttributeError:
            self.copy_catalog()
        try:
            stime4down  = obspy.core.utcdatetime.UTCDateTime(start_date)
        except:
            stime4down  = obspy.UTCDateTime(0)
        try:
            etime4down  = obspy.core.utcdatetime.UTCDateTime(end_date)
        except:
            etime4down  = obspy.UTCDateTime()
        for event in self.cat:
            pmag            = event.preferred_magnitude()
            magnitude       = pmag.mag
            Mtype           = pmag.magnitude_type
            event_descrip   = event.event_descriptions[0].text+', '+event.event_descriptions[0].type
            porigin         = event.preferred_origin()
            otime           = porigin.time
            timestr         = otime.isoformat()
            evlo            = porigin.longitude
            evla            = porigin.latitude
            evdp            = porigin.depth/1000.
            
            if otime < stime4down or otime > etime4down:
                continue
            if lon0 is not None and lat0 is not None:
                dist, az, baz   = obspy.geodetics.gps2dist_azimuth(evla, evlo, lat0, lon0) # distance is in m
                dist            = dist/1000.
                starttime       = otime+dist/vmax
                endtime         = otime+dist/vmin
                commontime      = True
                # start time stampe
                year            = starttime.year
                month           = starttime.month
                day             = starttime.day
                hour            = starttime.hour
                minute          = starttime.minute
                second          = starttime.second
                # end time stampe
                year2           = endtime.year
                month2          = endtime.month
                day2            = endtime.day
                hour2           = endtime.hour
                minute2         = endtime.minute
                second2         = endtime.second
            else:
                commontime      = False
            oyear               = otime.year
            omonth              = otime.month
            oday                = otime.day
            ohour               = otime.hour
            omin                = otime.minute
            osec                = otime.second
            header_str2         = header_str1 +'.LABEL %s_%d_%s_%d_%d_%d_%d\n' %(label, oyear, mondict[omonth], oday, ohour, omin, osec)
            header_str2         += '.QUALITY %s\n' %quality +'.END\n'
            out_str             = ''
            # loop over stations
            Nsta            = 0
            for network in self.inv:
                for station in network:
                    netcode = network.code
                    stacode = station.code
                    staid   = netcode+'.'+stacode
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        st_date     = station.start_date
                        ed_date     = station.end_date
                    if skipinv and (otime < st_date or otime > ed_date):
                        continue
                    channel_type    = None
                    for chantype in chanrank:
                        tmpch       = station.select(channel = chantype+'?')
                        if len(tmpch) >= len(channels):
                            channel_type    = chantype
                            break
                    if channel_type is None:
                        if verbose:
                            print('!!! NO selected channel types: '+ staid)
                        continue
                    stlo            = station.longitude
                    stla            = station.latitude
                    if commontime:
                        day_str     = '%d %d %d %d %d %d %d %d %d %d %d %d' %(year, month, day, hour, minute, second, \
                                            year2, month2, day2, hour2, minute2, second2)
                    else:
                        dist, az, baz   = obspy.geodetics.gps2dist_azimuth(evla, evlo, stla, stlo) # distance is in m
                        dist            = dist/1000.
                        starttime       = otime+dist/vmax
                        endtime         = otime+dist/vmin
                        # start time stampe
                        year            = starttime.year
                        month           = starttime.month
                        day             = starttime.day
                        hour            = starttime.hour
                        minute          = starttime.minute
                        second          = starttime.second
                        # end time stampe
                        year2           = endtime.year
                        month2          = endtime.month
                        day2            = endtime.day
                        hour2           = endtime.hour
                        minute2         = endtime.minute
                        second2         = endtime.second
                        day_str         = '%d %d %d %d %d %d %d %d %d %d %d %d' %(year, month, day, hour, minute, second, \
                                            year2, month2, day2, hour2, minute2, second2)
                    for tmpch in channels:
                        chan        = channel_type + tmpch
                        chan_str    = '1 %s' %chan
                        sta_str     = '%s %s %s %s\n' %(stacode, netcode, day_str, chan_str)
                        out_str     += sta_str
                    Nsta    += 1
            out_str     = header_str2 + out_str
            if Nsta == 0:
                print ('--- [RAYLEIGH DATA REQUEST] No data available in inventory, Event: %s %s' %(otime.isoformat(), event_descrip))
                continue
            #========================
            # send email to IRIS
            #========================
            server  = smtplib.SMTP('localhost')
            MSG     = title + out_str
            server.sendmail(FROM, TO, MSG)
            server.quit()
            print ('--- [RAYLEIGH DATA REQUEST] email sent to IRIS, Event: %s %s' %(otime.isoformat(), event_descrip))
        return
    
    def request_rayleigh_obs(self, lon0=None, lat0=None, minDelta=-1, maxDelta=181, chanrank=['L', 'B', 'H'], obs_channels = ['H1', 'H2', 'HZ', 'DH'],\
            vmax=6.0, vmin=1.0, verbose=False, start_date=None, end_date=None, skipinv=True, label='LF', quality = 'B', name = 'LiliFeng',\
            send_email=False, email_address='lfengmac@gmail.com', iris_email='breq_fast@iris.washington.edu'):
        """request Rayleigh wave data from IRIS server
        ====================================================================================================================
        ::: input parameters :::
        lon0, lat0      - center of array. If specified, all waveform will have the same starttime and endtime
        min/maxDelta    - minimum/maximum epicentral distance, in degree
        channel         - Channel code, e.g. 'BHZ'.
                            Last character (i.e. component) can be a wildcard (‘?’ or ‘*’) to fetch Z, N and E component.
        vmin, vmax      - minimum/maximum velocity for surface wave window
        =====================================================================================================================
        """
        header_str1     = '.NAME %s\n' %name + '.INST CU\n'+'.MAIL University of Colorado Boulder\n'
        header_str1     += '.EMAIL %s\n' %email_address+'.PHONE\n'+'.FAX\n'+'.MEDIA: Electronic (FTP)\n'
        header_str1     += '.ALTERNATE MEDIA: Electronic (FTP)\n'
        FROM            = 'no_reply@surfpy.com'
        TO              = iris_email
        title           = 'Subject: Requesting Data\n\n'
        try:
            print (self.cat)
        except AttributeError:
            self.copy_catalog()
        try:
            stime4down  = obspy.core.utcdatetime.UTCDateTime(start_date)
        except:
            stime4down  = obspy.UTCDateTime(0)
        try:
            etime4down  = obspy.core.utcdatetime.UTCDateTime(end_date)
        except:
            etime4down  = obspy.UTCDateTime()
        for event in self.cat:
            pmag            = event.preferred_magnitude()
            magnitude       = pmag.mag
            Mtype           = pmag.magnitude_type
            event_descrip   = event.event_descriptions[0].text+', '+event.event_descriptions[0].type
            porigin         = event.preferred_origin()
            otime           = porigin.time
            timestr         = otime.isoformat()
            evlo            = porigin.longitude
            evla            = porigin.latitude
            evdp            = porigin.depth/1000.
            if otime < stime4down or otime > etime4down:
                continue
            if lon0 is not None and lat0 is not None:
                dist, az, baz   = obspy.geodetics.gps2dist_azimuth(evla, evlo, lat0, lon0) # distance is in m
                dist            = dist/1000.
                starttime       = otime+dist/vmax
                endtime         = otime+dist/vmin
                commontime      = True
                # start time stampe
                year            = starttime.year
                month           = starttime.month
                day             = starttime.day
                hour            = starttime.hour
                minute          = starttime.minute
                second          = starttime.second
                # end time stampe
                year2           = endtime.year
                month2          = endtime.month
                day2            = endtime.day
                hour2           = endtime.hour
                minute2         = endtime.minute
                second2         = endtime.second
            else:
                commontime      = False
            oyear               = otime.year
            omonth              = otime.month
            oday                = otime.day
            ohour               = otime.hour
            omin                = otime.minute
            osec                = otime.second
            header_str2         = header_str1 +'.LABEL %s_%d_%s_%d_%d_%d_%d\n' %(label, oyear, mondict[omonth], oday, ohour, omin, osec)
            header_str2         += '.QUALITY %s\n' %quality +'.END\n'
            out_str             = ''
            # loop over stations
            Nsta            = 0
            for network in self.inv:
                for station in network:
                    netcode = network.code
                    stacode = station.code
                    staid   = netcode+'.'+stacode
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        st_date     = station.start_date
                        ed_date     = station.end_date
                    if skipinv and (otime < st_date or otime > ed_date):
                        continue
                    channel_type    = None
                    for chantype in chanrank:
                        tmpch       = station.select(channel = chantype+'??')
                        if len(tmpch) >= len(obs_channels):
                            channel_type    = chantype
                            break
                    if channel_type is None:
                        if verbose:
                            print('!!! NO selected channel types: '+ staid)
                        continue
                    stlo            = station.longitude
                    stla            = station.latitude
                    if commontime:
                        day_str     = '%d %d %d %d %d %d %d %d %d %d %d %d' %(year, month, day, hour, minute, second, \
                                            year2, month2, day2, hour2, minute2, second2)
                    else:
                        dist, az, baz   = obspy.geodetics.gps2dist_azimuth(evla, evlo, stla, stlo) # distance is in m
                        dist            = dist/1000.
                        starttime       = otime+dist/vmax
                        endtime         = otime+dist/vmin
                        # start time stampe
                        year            = starttime.year
                        month           = starttime.month
                        day             = starttime.day
                        hour            = starttime.hour
                        minute          = starttime.minute
                        second          = starttime.second
                        # end time stampe
                        year2           = endtime.year
                        month2          = endtime.month
                        day2            = endtime.day
                        hour2           = endtime.hour
                        minute2         = endtime.minute
                        second2         = endtime.second
                        day_str         = '%d %d %d %d %d %d %d %d %d %d %d %d' %(year, month, day, hour, minute, second, \
                                            year2, month2, day2, hour2, minute2, second2)
                    for tmpch in obs_channels:
                        chan        = channel_type + tmpch
                        chan_str    = '1 %s' %chan
                        sta_str     = '%s %s %s %s\n' %(stacode, netcode, day_str, chan_str)
                        out_str     += sta_str
                    Nsta    += 1
            out_str     = header_str2 + out_str
            if Nsta == 0:
                print ('--- [RAYLEIGH DATA REQUEST] No data available in inventory, Event: %s %s' %(otime.isoformat(), event_descrip))
                continue
            #========================
            # send email to IRIS
            #========================
            server  = smtplib.SMTP('localhost')
            MSG     = title + out_str
            server.sendmail(FROM, TO, MSG)
            server.quit()
            print ('--- [RAYLEIGH DATA REQUEST] email sent to IRIS, Event: %s %s' %(otime.isoformat(), event_descrip))
        return

    def request_rf(self, minDelta=30, maxDelta=150, chanrank=['BH', 'HH'], channels = 'ENZ', phase='P',\
            startoffset=-30., endoffset=60.0, verbose=False, start_date=None, end_date=None, skipinv=True,\
            label='LF', quality = 'B', name = 'LiliFeng', email_address='lfengmac@gmail.com', iris_email='breq_fast@iris.washington.edu'):
        """request receiver function data from IRIS server
        ====================================================================================================================
        ::: input parameters :::
        min/maxDelta    - minimum/maximum epicentral distance, in degree
        channels        - Channel code, e.g. 'BHZ'.
                            Last character (i.e. component) can be a wildcard (‘?’ or ‘*’) to fetch Z, N and E component.
        min/maxDelta    - minimum/maximum epicentral distance, in degree
        channel_rank    - rank of channel types
        phase           - body wave phase to be downloaded, arrival time will be computed using taup
        start/endoffset - start and end offset for downloaded data
        =====================================================================================================================
        """
        header_str1     = '.NAME %s\n' %name + '.INST CU\n'+'.MAIL University of Colorado Boulder\n'
        header_str1     += '.EMAIL %s\n' %email_address+'.PHONE\n'+'.FAX\n'+'.MEDIA: Electronic (FTP)\n'
        header_str1     += '.ALTERNATE MEDIA: Electronic (FTP)\n'
        FROM            = 'no_reply@surfpy.com'
        TO              = iris_email
        title           = 'Subject: Requesting Data\n\n'
        try:
            print (self.cat)
        except AttributeError:
            self.copy_catalog()
        try:
            stime4down  = obspy.core.utcdatetime.UTCDateTime(start_date)
        except:
            stime4down  = obspy.UTCDateTime(0)
        try:
            etime4down  = obspy.core.utcdatetime.UTCDateTime(end_date)
        except:
            etime4down  = obspy.UTCDateTime()
        for event in self.cat:
            pmag            = event.preferred_magnitude()
            magnitude       = pmag.mag
            Mtype           = pmag.magnitude_type
            event_descrip   = event.event_descriptions[0].text+', '+event.event_descriptions[0].type
            porigin         = event.preferred_origin()
            otime           = porigin.time
            timestr         = otime.isoformat()
            evlo            = porigin.longitude
            evla            = porigin.latitude
            evdp            = porigin.depth/1000.
            
            if otime < stime4down or otime > etime4down:
                continue
            oyear               = otime.year
            omonth              = otime.month
            oday                = otime.day
            ohour               = otime.hour
            omin                = otime.minute
            osec                = otime.second
            header_str2         = header_str1 +'.LABEL %s_%d_%s_%d_%d_%d_%d\n' %(label, oyear, mondict[omonth], oday, ohour, omin, osec)
            header_str2         += '.QUALITY %s\n' %quality +'.END\n'
            out_str             = ''
            # loop over stations
            Nsta            = 0
            for network in self.inv:
                for station in network:
                    netcode = network.code
                    stacode = station.code
                    staid   = netcode+'.'+stacode
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        st_date     = station.start_date
                        ed_date     = station.end_date
                    if skipinv and (otime < st_date or otime > ed_date):
                        continue
                    # determine channel type
                    channel_type    = None
                    for chantype in chanrank:
                        tmpchE      = station.select(channel = chantype+'E')
                        tmpchN      = station.select(channel = chantype+'N')
                        tmpchZ      = station.select(channel = chantype+'Z')
                        if len(tmpchE)>0 and len(tmpchN)>0 and len(tmpchZ)>0:
                            channel_type    = chantype
                            break
                    if channel_type is None:
                        if verbose:
                            print('!!! NO selected channel types: '+ staid)
                        continue
                    stlo            = station.longitude
                    stla            = station.latitude
                    az, baz, dist   = geodist.inv(evlo, evla, stlo, stla)
                    dist            = dist/1000.
                    if baz<0.:
                        baz         += 360.
                    Delta           = obspy.geodetics.kilometer2degrees(dist)
                    if Delta<minDelta:
                        continue
                    if Delta>maxDelta:
                        continue
                    arrivals            = taupmodel.get_travel_times(source_depth_in_km=evdp, distance_in_degree=Delta, phase_list=[phase])#, receiver_depth_in_km=0)
                    try:
                        arr             = arrivals[0]
                        arrival_time    = arr.time
                        rayparam        = arr.ray_param_sec_degree
                    except IndexError:
                        continue
                    starttime       = otime + arrival_time + startoffset
                    endtime         = otime + arrival_time + endoffset
                    # start time stampe
                    year            = starttime.year
                    month           = starttime.month
                    day             = starttime.day
                    hour            = starttime.hour
                    minute          = starttime.minute
                    second          = starttime.second
                    # end time stampe
                    year2           = endtime.year
                    month2          = endtime.month
                    day2            = endtime.day
                    hour2           = endtime.hour
                    minute2         = endtime.minute
                    second2         = endtime.second
                    day_str         = '%d %d %d %d %d %d %d %d %d %d %d %d' %(year, month, day, hour, minute, second, \
                                        year2, month2, day2, hour2, minute2, second2)
                    for tmpch in channels:
                        chan        = channel_type + tmpch
                        chan_str    = '1 %s' %chan
                        sta_str     = '%s %s %s %s\n' %(stacode, netcode, day_str, chan_str)
                        out_str     += sta_str
                    Nsta    += 1
            out_str     = header_str2 + out_str
            if Nsta == 0:
                print ('--- [RF DATA REQUEST] No data available in inventory, Event: %s %s' %(otime.isoformat(), event_descrip))
                continue
            #========================
            # send email to IRIS
            #========================
            server  = smtplib.SMTP('localhost')
            MSG     = title + out_str
            server.sendmail(FROM, TO, MSG)
            server.quit()
            print ('--- [RF DATA REQUEST] email sent to IRIS, Event: %s %s' %(otime.isoformat(), event_descrip))
        return
    