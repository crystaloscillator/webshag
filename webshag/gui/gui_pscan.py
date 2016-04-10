# -*- coding: utf-8 -*-
## ################################################################# ##
## (C) SCRT - Information Security, 2007 - 2008 // author: ~SaD~     ##
## ################################################################# ##
## This program is free software: you can redistribute it and/or     ##
## modify it under the terms of the GNU General Public License as    ##
## published by the Free Software Foundation, either version 3 of    ##
## the License, or (at your option) any later version.               ##
## This program is distributed in the hope that it will be useful,   ##
## but WITHOUT ANY WARRANTY; without even the implied warranty of    ##
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the     ##
## GNU General Public License for more details.                      ##
## You should have received a copy of the GNU General Public License ##
## along with this program. If not, see http://www.gnu.org/licenses. ##
## ################################################################# ##
## last mod: 2008-11-03

from __future__ import with_statement
import wx
import threading
from time import strftime, localtime

from webshag.core import core_utilities
from webshag.modules import module_pscan


## ################################################################# ##
## MODULE CONSTANTS
## ################################################################# ##

MODULE_PSCAN = 'pscan'
REFRESH_RATE = 500
TEXT_IDLE = u'Idle'
TEXT_LAST = u'Last scan finished @ '
TEXT_RUNNING = u'Nmap running. Please wait... '
TEXT_INVALID = u'Invalid Input !'


## ################################################################# ##
## CLASS: Panel
## ################################################################# ##

class Panel(wx.Panel):
    
    def __init__(self, parent, coordinator):
        
        wx.Panel.__init__(self, parent)
        self.__coordinator = coordinator
        
        # Variables ############################################
        self.__tool = MODULE_PSCAN
        self.__results = []
        self.__openPorts = {}
        self.__switch = [False]
        self.__switch_lock = threading.RLock()
        self.__results_lock = threading.RLock()
        
        # Widgets ##############################################
        self.__hostText = wx.TextCtrl(self, -1, '')
        self.__okButton = wx.Button(self, wx.ID_OK, u'&OK')
        self.__outputList = wx.ListBox(self, -1, style=wx.LB_SINGLE)
        self.__outputLogText = wx.TextCtrl(self, -1, '', style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.__outputDetailsText = wx.TextCtrl(self, -1, '', style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.__statusText = wx.StaticText(self, -1, TEXT_IDLE)   
        self.__timer = wx.Timer(self, -1)
        
        # Event Bindings #######################################
        self.Bind(wx.EVT_BUTTON, self.__onOKButton, id=self.__okButton.GetId())
        self.Bind(wx.EVT_TIMER, self.__onTimer, id=self.__timer.GetId())
        self.Bind(wx.EVT_LISTBOX, self.__onSelect, id=self.__outputList.GetId())
        
        # Layout Management ####################################
        controlSizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Settings'), orient=wx.HORIZONTAL)
        controlSizerGrid = wx.GridBagSizer()
        controlSizerGrid.Add(wx.StaticText(self, -1, u'Target [host | IPv4]:'), (0, 0), (1, 2), wx.ALIGN_BOTTOM | wx.TOP, 5)
        controlSizerGrid.Add(self.__hostText, (1, 0), (1, 1), wx.EXPAND)
        controlSizerGrid.Add(self.__okButton, (1, 1), (1, 1), wx.EXPAND | wx.LEFT, 5)
        controlSizerGrid.AddGrowableCol(0)
        controlSizer.Add(controlSizerGrid, 1, wx.EXPAND)
        
        resultSizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Results'), orient=wx.VERTICAL)
        resultSizerGrid = wx.GridBagSizer()
        resultSizerGrid.Add(wx.StaticText(self, -1, u'Open Ports:'), (0, 0), (1, 1), wx.LEFT | wx.ALIGN_BOTTOM, 5)
        resultSizerGrid.Add(self.__outputList, (1, 0), (3, 1), wx.EXPAND | wx.ALL, 5)
        resultSizerGrid.Add(wx.StaticText(self, -1, u'Port Details:'), (0, 1), (1, 1), wx.LEFT | wx.ALIGN_BOTTOM, 5)
        resultSizerGrid.Add(self.__outputDetailsText, (1, 1), (3, 1), wx.EXPAND | wx.ALL, 5)
        resultSizerGrid.Add(wx.StaticText(self, -1, u'Console:'), (4, 0), (1, 2), wx.LEFT | wx.ALIGN_BOTTOM, 5)
        resultSizerGrid.Add(self.__outputLogText, (5, 0), (1, 2), wx.EXPAND | wx.ALL, 5)
        resultSizerGrid.AddGrowableCol(1)
        resultSizerGrid.AddGrowableRow(1)
        resultSizerGrid.AddGrowableRow(2)
        resultSizerGrid.AddGrowableRow(3)
        resultSizerGrid.AddGrowableRow(5)
        resultSizer.Add(resultSizerGrid, 1, wx.EXPAND)
        
        statusSizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Status'), orient=wx.VERTICAL)
        statusSizer.Add(self.__statusText, 1, wx.EXPAND)
        
        rootSizer = wx.GridBagSizer()
        rootSizer.Add(controlSizer, (0, 0), (1, 1), wx.EXPAND | wx.ALL, 5)
        rootSizer.Add(resultSizer, (1, 0), (1, 1), wx.EXPAND | wx.ALL, 5)
        rootSizer.Add(statusSizer, (2, 0), (1, 1), wx.EXPAND | wx.ALL, 5)
        rootSizer.AddGrowableRow(1)
        rootSizer.AddGrowableCol(0)
        rootSizer.AddGrowableCol(1)
        
        self.SetSizer(rootSizer)
    
    ## EVENT HANDLING METHODS ########################################## ##
    ## ################################################################# ##
    
    def __onSelect(self, event):
        if len(self.__openPorts.keys()) > 0:
            index = self.__outputList.GetSelection()
            port = self.__outputList.GetString(index)
            self.__outputDetailsText.SetValue(self.__openPorts[port])
    
    def __onOKButton(self, event):
        self.__start()

    def __onTimer(self, event):
        with self.__switch_lock:
            if self.__switch[0]:
                pass
            else:
                self.__timer.Stop()
                self.__print_results()
                self.__okButton.Enable(True)
                with self.__results_lock:
                    self.__coordinator.notify_stop(self.__tool, self.__results)

    ## DISPLAY RELATED METHODS ######################################### ##
    ## ################################################################# ##

    def __print_start(self):
        self.__outputList.Clear()
        self.__outputLogText.Clear()
        self.__outputDetailsText.Clear()
        self.__statusText.SetLabel(TEXT_RUNNING)
    
    def __print_invalid(self):
        self.__outputList.Clear()
        self.__outputLogText.Clear()
        self.__outputDetailsText.Clear()
        self.__statusText.SetLabel(TEXT_INVALID)
    
    def __print_results(self):
        error = False
        with self.__results_lock:
            for result in self.__results:
    
                if result.has_key(u'ERROR'):
                    self.__outputLogText.AppendText( u'ERROR\t' + result[u'ERROR'] + u'\n')
                    error = True
                    
                elif result.has_key(u'TARGET'):
                    self.__outputLogText.AppendText( u'INFO\tScan of ' + result[u'TARGET'] + u' finished\n')
                    
                elif result.has_key(u'PORTID') and result.has_key(u'PROTOCOL'):
                   
                    details = u'PORT:\t\t' + result['PORTID'] + u' (' + result[u'PROTOCOL'].upper() + ')\n'
                    details += u''
                    
                    if result.has_key(u'SRV_NAME'):
                        details += 'SERVICE:\t\t' + result['SRV_NAME'] + u'\n'
                        
                    if result.has_key(u'SRV_PRODUCT'):
                        details += 'PRODUCT:\t' + result['SRV_PRODUCT'] + u'\n'
                    
                    if result.has_key(u'SRV_OS'):
                        details += 'SYSTEM:\t\t' + result['SRV_OS'] + u'\n'
                   
                    self.__openPorts[result[u'PORTID']] = details
        
        if not error:
            self.__outputLogText.AppendText( u'INFO\tFound ' + unicode(len(self.__openPorts)) + u' open ports.\n')
            
        self.__outputList.Set(sorted(self.__openPorts.keys()))
        self.__statusText.SetLabel(TEXT_IDLE + u'. ' + TEXT_LAST + strftime("%d/%m/%Y %H:%M:%S", localtime()))

    ## MISC METHODS #################################################### ##
    ## ################################################################# ##

    def __start(self):
        with self.__switch_lock:
            if not self.__switch[0]:
                self.__load_entries()
                if self.__check_entries():
                    self.__coordinator.notify_start(self.__tool)
                    self.__switch[0] = True
                    self.__okButton.Enable(False)
                    self.__results = []
                    self.__openPorts = {}
                    self.__print_start()
                    Thread(self.__host, self.__results, self.__results_lock, self.callback_stop).start()
                    self.__timer.Start(REFRESH_RATE)
                else:
                    self.__print_invalid()
            else:
                pass
    
    def __stop(self):
        with self.__switch_lock:
            self.__switch[0] = False
    
    def __load_entries(self):
        self.__host = self.__hostText.GetValue().strip()
    
    def __check_entries(self):
        return core_utilities.check_host(self.__host)
    
    def callback_stop(self):
        self.__stop()


## ################################################################# ##
## CLASS: Thread
## ################################################################# ##

class Thread(threading.Thread):
    
    def __init__(self, host, results, results_lock, callback_stop):
        
        threading.Thread.__init__(self)
        self.__host = host
        self.__results = results
        self.__results_lock = results_lock
        self.__callback_stop = callback_stop
    
    def run(self):
        module_pscan.perform(self.__host, False, self.__results, self.__results_lock, [True], threading.Lock())
        self.__callback_stop()