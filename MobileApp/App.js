import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Linking, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import * as Battery from 'expo-battery';

const INITIAL_FILES = [
  { id: '1', name: 'capture-001.jpg', type: 'Image', size: '3.5 MB', created: '2 min ago' },
  { id: '2', name: 'voice-note.wav', type: 'Audio', size: '1.2 MB', created: '5 min ago' },
  { id: '3', name: 'ai-response.txt', type: 'Text', size: '12 KB', created: '8 min ago' },
  { id: '4', name: 'nav-temp.dat', type: 'Navigation', size: '6 MB', created: '10 min ago' },
  { id: '5', name: 'diagnostic.log', type: 'Log', size: '1.8 MB', created: '12 min ago' },
  { id: '6', name: 'temp-output.json', type: 'AI output', size: '0.9 MB', created: '15 min ago' },
];

const STORAGE_KEY = '@argus-hub/local-state';
const AUTO_DELETE_MS = { '1 hour': 3600000, '24 hours': 86400000, '7 days': 604800000 };

function StatusBadge({ online, label }) {
  return (
    <View style={[styles.badge, online ? styles.badgeOnline : styles.badgeOffline]}>
      <View style={[styles.dot, online ? styles.dotOnline : styles.dotOffline]} />
      <Text style={styles.badgeText}>{label}</Text>
    </View>
  );
}

function Card({ title, children, danger = false }) {
  return <View style={[styles.card, danger && styles.dangerCard]}><Text style={styles.cardTitle}>{title}</Text>{children}</View>;
}

function Button({ label, onPress, primary = false, danger = false, disabled = false }) {
  return (
    <TouchableOpacity disabled={disabled} onPress={onPress} style={[styles.button, primary && styles.buttonPrimary, danger && styles.buttonDanger, disabled && styles.buttonDisabled]}>
      <Text style={[styles.buttonText, primary && styles.buttonTextPrimary]}>{label}</Text>
    </TouchableOpacity>
  );
}

export default function App() {
  const [tab, setTab] = useState('Dashboard');
  const [connected, setConnected] = useState(false);
  const [battery, setBattery] = useState(82);
  const [charging, setCharging] = useState(false);
  const [lowPower, setLowPower] = useState(false);
  const [gpsActive, setGpsActive] = useState(true);
  const [files, setFiles] = useState(INITIAL_FILES);
  const [showFiles, setShowFiles] = useState(false);
  const [autoDelete, setAutoDelete] = useState('24 hours');
  const [locationText, setLocationText] = useState('Location not requested');
  const [accuracy, setAccuracy] = useState(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [storageReady, setStorageReady] = useState(false);
  const [batteryAvailable, setBatteryAvailable] = useState(false);
  const [emergencyContacts, setEmergencyContacts] = useState([]);
  const [contactName, setContactName] = useState('');
  const [contactPhone, setContactPhone] = useState('');

  const lowBattery = battery <= 15;
  const remaining = useMemo(() => {
    if (lowBattery) return 'Less than 30 min';
    if (lowPower) return '6h 10m';
    return '4h 20m';
  }, [lowBattery, lowPower]);
  const location = gpsActive ? locationText : 'GPS disabled';

  useEffect(() => {
    const restore = async () => {
      try {
        const saved = await AsyncStorage.getItem(STORAGE_KEY);
        if (saved) {
          const value = JSON.parse(saved);
          setFiles(Array.isArray(value.files) ? value.files : INITIAL_FILES);
          setAutoDelete(value.autoDelete || '24 hours');
          setLowPower(Boolean(value.lowPower));
          setEmergencyContacts(Array.isArray(value.emergencyContacts) ? value.emergencyContacts : []);
        }
      } catch (error) { console.warn('Could not restore local data', error); }
      setStorageReady(true);
    };
    restore();
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    AsyncStorage.setItem(STORAGE_KEY, JSON.stringify({ files, autoDelete, lowPower, emergencyContacts })).catch((error) => console.warn('Could not save local data', error));
  }, [files, autoDelete, lowPower, emergencyContacts, storageReady]);

  useEffect(() => {
    const updateBattery = async () => {
      try {
        const [level, state] = await Promise.all([Battery.getBatteryLevelAsync(), Battery.getBatteryStateAsync()]);
        if (level >= 0) { setBattery(Math.round(level * 100)); setBatteryAvailable(true); }
        setCharging(state === Battery.BatteryState.CHARGING || state === Battery.BatteryState.FULL);
      } catch (error) { console.warn('Could not read phone battery', error); }
    };
    updateBattery();
    const levelSubscription = Battery.addBatteryLevelListener(({ batteryLevel }) => { if (batteryLevel >= 0) { setBattery(Math.round(batteryLevel * 100)); setBatteryAvailable(true); } });
    const stateSubscription = Battery.addBatteryStateListener(({ batteryState }) => setCharging(batteryState === Battery.BatteryState.CHARGING || batteryState === Battery.BatteryState.FULL));
    return () => { levelSubscription.remove(); stateSubscription.remove(); };
  }, []);

  useEffect(() => {
    if (!storageReady) return;
    setFiles((items) => items.filter((file) => !file.createdAt || Date.now() - file.createdAt < AUTO_DELETE_MS[autoDelete]));
  }, [autoDelete, storageReady]);

  const refreshLocation = async () => {
    setLocationLoading(true);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== 'granted') { setLocationText('Location permission was not granted'); setAccuracy(null); return; }
      const position = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
      setAccuracy(Math.round(position.coords.accuracy || 0));
      const places = await Location.reverseGeocodeAsync(position.coords);
      const place = places[0];
      setLocationText(place ? [place.city || place.district, place.region, place.country].filter(Boolean).join(', ') : `${position.coords.latitude.toFixed(5)}, ${position.coords.longitude.toFixed(5)}`);
    } catch (error) { setLocationText('Unable to get current location'); setAccuracy(null); }
    finally { setLocationLoading(false); }
  };

  const toggleGPS = () => {
    if (gpsActive) setGpsActive(false);
    else { setGpsActive(true); refreshLocation(); }
  };

  const shareLocation = () => Alert.alert('Location ready to share', gpsActive ? `${location}${accuracy ? `\nAccuracy: +/- ${accuracy} m` : ''}` : 'Location is not available yet.');
  const sendSOS = () => {
    const primaryContact = emergencyContacts[0];
    const target = primaryContact ? primaryContact.phone : '112';
    const targetLabel = primaryContact ? `${primaryContact.name || 'Emergency contact'} (${primaryContact.phone})` : 'India emergency services (112)';
    Alert.alert(
      'Start SOS call?',
      `This will open your phone dialer for ${targetLabel}. Use SOS only in a genuine emergency.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: primaryContact ? 'CALL CONTACT' : 'CALL 112',
          style: 'destructive',
          onPress: async () => {
            try {
              const canCall = await Linking.canOpenURL(`tel:${target}`);
              if (!canCall) throw new Error('Dialer unavailable');
              await Linking.openURL(`tel:${target}`);
            } catch (error) {
              Alert.alert('Unable to open dialer', 'Please call 112 manually.');
            }
          },
        },
      ],
    );
  };
  const addEmergencyContact = () => {
    const phone = contactPhone.replace(/[^0-9+]/g, '');
    if (!phone) { Alert.alert('Phone number required', 'Enter a valid emergency contact number.'); return; }
    if (emergencyContacts.length >= 3) { Alert.alert('Maximum reached', 'You can save up to three emergency contacts.'); return; }
    setEmergencyContacts((items) => [...items, { id: String(Date.now()), name: contactName.trim() || 'Emergency contact', phone }]);
    setContactName('');
    setContactPhone('');
  };
  const clearFiles = () => Alert.alert('Clear temporary files?', 'These local, temporary files will be deleted.', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Clear files', style: 'destructive', onPress: () => setFiles([]) },
  ]);

  const renderDashboard = () => (
    <>
      <Card title="SMART GLASSES">
        <View style={styles.titleRow}><StatusBadge online={connected} label={connected ? 'CONNECTED' : 'DISCONNECTED'} /><Text style={styles.bluetooth}>Bluetooth</Text></View>
        <Text style={styles.mainText}>{connected ? 'A.R.G.U.S.-GLASSES-01' : 'Smart glasses are not connected'}</Text>
        {connected && <Text style={styles.mutedText}>BLE Signal: Strong</Text>}
        {!connected && <Text style={styles.mutedText}>Phone-only mode is active. Pair a Raspberry Pi glasses device to enable hardware data.</Text>}
        <Button label={connected ? 'DISCONNECT' : 'PAIR GLASSES'} onPress={() => connected ? setConnected(false) : Alert.alert('Glasses pairing', 'Raspberry Pi Bluetooth integration will be available when device UUIDs are configured.')} primary={!connected} />
      </Card>

      <Card title="PHONE BATTERY">
        <View style={styles.batteryHeader}><View style={[styles.batteryShape, lowBattery && styles.batteryLow]}><View style={[styles.batteryFill, { width: `${battery}%` }]} /></View><Text style={styles.percent}>{battery}%</Text></View>
        <Text style={[styles.batteryStatus, lowBattery && styles.lowText]}>{lowBattery ? 'LOW PHONE BATTERY' : 'Battery Status: Good'}</Text>
        <Text style={styles.mutedText}>Estimated Remaining: {remaining}</Text>
        <Text style={styles.mutedText}>Source: {batteryAvailable ? 'Phone battery sensor' : 'Battery sensor unavailable'} · {charging ? 'Charging' : 'Not charging'}</Text>
        {lowBattery && <Text style={styles.warning}>Please charge your phone.</Text>}
        <Button label={lowPower ? 'APP LOW POWER ON' : 'APP LOW POWER MODE'} onPress={() => setLowPower((value) => !value)} primary />
      </Card>

      <Card title="GPS / LOCATION">
        <StatusBadge online={gpsActive} label={gpsActive ? 'GPS ACTIVE' : 'GPS UNAVAILABLE'} />
        <Text style={styles.mainText}>{gpsActive ? (locationLoading ? 'Getting current location...' : 'Location available') : 'GPS is disabled'}</Text>
        <Text style={styles.mutedText}>Accuracy: {gpsActive && accuracy ? `+/- ${accuracy} m` : 'Unavailable'}</Text>
        <Text style={styles.location}>{location}</Text>
        <View style={styles.actionRow}><Button label={gpsActive ? 'DISABLE GPS' : 'ENABLE GPS'} onPress={toggleGPS} primary={!gpsActive} /><Button label="REFRESH GPS" onPress={refreshLocation} disabled={!gpsActive || locationLoading} /></View>
        <Button label="SHARE LOCATION" onPress={shareLocation} disabled={!gpsActive || locationLoading} />
      </Card>

      <Card title="DEVICE TELEMETRY"><Info label="Device" value="Phone" /><Info label="Battery source" value={batteryAvailable ? 'Live sensor' : 'Unavailable'} /><Info label="Glasses link" value="Not paired" /></Card>
      <Card title="AI VISION PIPELINE"><Text style={styles.pipelineSelected}>● Cloud — Claude API</Text><Text style={styles.pipeline}>○ Auto — Hybrid</Text><Text style={styles.pipeline}>○ Offline — YOLO</Text></Card>
      <Card title="HARDWARE CONTROLS"><Info label="Brightness" value="80%" /><Info label="Microphone" value="Active" /><Info label="Camera" value="Standby" /></Card>
      <Card title="EMERGENCY SOS" danger><Text style={styles.mutedText}>{emergencyContacts.length ? `Primary contact: ${emergencyContacts[0].name} · ${emergencyContacts[0].phone}` : 'No emergency contact saved — SOS will dial India emergency number 112.'}</Text><Button label={emergencyContacts.length ? 'CALL PRIMARY SOS CONTACT' : 'CALL 112 EMERGENCY SOS'} danger onPress={sendSOS} /></Card>
    </>
  );

  const renderNavigation = () => <><Card title="GPS / LOCATION"><StatusBadge online={gpsActive} label={gpsActive ? 'GPS ACTIVE' : 'GPS UNAVAILABLE'} /><Text style={styles.location}>{location}</Text><Text style={styles.mutedText}>{gpsActive && accuracy ? `Accuracy: +/- ${accuracy} m` : 'Refresh GPS to retrieve device location.'}</Text><Button label={gpsActive ? 'REFRESH GPS' : 'ENABLE GPS'} onPress={gpsActive ? refreshLocation : toggleGPS} primary /></Card><Card title="NAVIGATION"><Text style={styles.mainText}>{gpsActive ? 'Ready for directions' : 'GPS is required for navigation'}</Text><Text style={styles.mutedText}>Glasses navigation data stays temporary unless you choose to save or share it.</Text></Card></>;

  const renderSettings = () => <><Card title="SETTINGS"><Text style={styles.mutedText}>Manage A.R.G.U.S. Hub preferences and local device data.</Text></Card><Card title="EMERGENCY CONTACTS"><Text style={styles.note}>SOS calls the first saved contact. If none is saved, it opens the phone dialer for 112.</Text><TextInput style={styles.input} value={contactName} onChangeText={setContactName} placeholder="Contact name" placeholderTextColor="#91a8c4" /><TextInput style={styles.input} value={contactPhone} onChangeText={setContactPhone} placeholder="Phone number" placeholderTextColor="#91a8c4" keyboardType="phone-pad" /><Button label="ADD EMERGENCY CONTACT" onPress={addEmergencyContact} primary />{emergencyContacts.map((contact, index) => <View style={styles.fileRow} key={contact.id}><View style={styles.fileInfo}><Text style={styles.fileName}>{index === 0 ? 'PRIMARY · ' : ''}{contact.name}</Text><Text style={styles.fileMeta}>{contact.phone}</Text></View><TouchableOpacity onPress={() => setEmergencyContacts((items) => items.filter((item) => item.id !== contact.id))}><Text style={styles.delete}>Delete</Text></TouchableOpacity></View>)}</Card><Card title="TEMPORARY STORAGE"><Text style={styles.storageNumber}>Files: {files.length}</Text><Text style={styles.mutedText}>Storage Used: {files.length ? '24 MB' : '0 MB'}</Text><Text style={styles.note}>Local to this app. Files are not uploaded unless you explicitly share them. File list and cleanup preference persist after restart.</Text><View style={styles.actionRow}><Button label={showFiles ? 'HIDE FILES' : 'VIEW FILES'} onPress={() => setShowFiles((value) => !value)} primary /><Button label="CLEAR TEMPORARY FILES" onPress={clearFiles} /></View><Text style={styles.settingLabel}>Auto-delete temporary files after</Text><View style={styles.periodRow}>{['1 hour', '24 hours', '7 days'].map((period) => <TouchableOpacity key={period} onPress={() => setAutoDelete(period)} style={[styles.period, autoDelete === period && styles.periodActive]}><Text style={styles.periodText}>{period}</Text></TouchableOpacity>)}</View>{showFiles && <View style={styles.fileList}>{files.length ? files.map((file) => <View style={styles.fileRow} key={file.id}><View style={styles.fileInfo}><Text style={styles.fileName}>{file.name}</Text><Text style={styles.fileMeta}>{file.type} · {file.size} · {file.created}</Text></View><TouchableOpacity onPress={() => setFiles((items) => items.filter((item) => item.id !== file.id))}><Text style={styles.delete}>Delete</Text></TouchableOpacity></View>) : <Text style={styles.empty}>No temporary files.</Text>}</View>}</Card></>;

  return <View style={styles.app}><StatusBar style="light" /><View style={styles.header}><Text style={styles.brand}>ARGUS SUPPORT</Text><Text style={styles.subtitle}>Smart glasses operational dashboard</Text></View><ScrollView contentContainerStyle={styles.content}>{tab === 'Dashboard' && renderDashboard()}{tab === 'Navigation' && renderNavigation()}{tab === 'Settings' && renderSettings()}</ScrollView><View style={styles.tabs}>{['Dashboard', 'Navigation', 'Settings'].map((item) => <TouchableOpacity key={item} style={[styles.tab, tab === item && styles.tabActive]} onPress={() => setTab(item)}><Text style={[styles.tabText, tab === item && styles.tabTextActive]}>{item}</Text></TouchableOpacity>)}</View></View>;
}

function Info({ label, value }) { return <View style={styles.info}><Text style={styles.mutedText}>{label}</Text><Text style={styles.infoValue}>{value}</Text></View>; }

const styles = StyleSheet.create({
  app: { flex: 1, backgroundColor: '#08111f' }, header: { paddingTop: 58, paddingHorizontal: 20, paddingBottom: 18, backgroundColor: '#101e33', borderBottomWidth: 1, borderColor: '#203957' }, brand: { color: '#f4f7ff', fontSize: 28, fontWeight: '900', letterSpacing: 1 }, subtitle: { color: '#9fb3ce', marginTop: 5, fontSize: 14 }, content: { padding: 16, paddingBottom: 94 }, card: { backgroundColor: '#11243d', borderWidth: 1, borderColor: '#203b5c', borderRadius: 18, padding: 18, marginBottom: 14 }, dangerCard: { borderColor: '#71414a', backgroundColor: '#2a1b28' }, cardTitle: { color: '#d6e6fb', fontSize: 13, letterSpacing: 1.1, fontWeight: '900', marginBottom: 14 }, titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }, bluetooth: { color: '#9bc2ff', fontWeight: '800', fontSize: 13 }, badge: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', paddingVertical: 7, paddingHorizontal: 10, borderRadius: 8 }, badgeOnline: { backgroundColor: '#123e35' }, badgeOffline: { backgroundColor: '#48252b' }, dot: { height: 9, width: 9, borderRadius: 5, marginRight: 7 }, dotOnline: { backgroundColor: '#42d6a3' }, dotOffline: { backgroundColor: '#ff6f73' }, badgeText: { color: '#fff', fontWeight: '900', fontSize: 13, letterSpacing: .5 }, mainText: { color: '#f6f8ff', fontSize: 17, fontWeight: '700', marginTop: 14 }, mutedText: { color: '#aebfd3', fontSize: 14, lineHeight: 21, marginTop: 5 }, input: { marginTop: 10, borderWidth: 1, borderColor: '#3c587a', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 12, color: '#fff', fontSize: 14, backgroundColor: '#0c1b30' }, button: { flex: 1, minHeight: 45, marginTop: 15, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 10, borderRadius: 10, borderWidth: 1, borderColor: '#446188', backgroundColor: '#172d4b' }, buttonPrimary: { backgroundColor: '#2e78dc', borderColor: '#4993f6' }, buttonDanger: { backgroundColor: '#b43748', borderColor: '#de5363' }, buttonDisabled: { opacity: .45 }, buttonText: { color: '#dbe9fa', fontWeight: '800', fontSize: 12, textAlign: 'center' }, buttonTextPrimary: { color: '#fff' }, actionRow: { flexDirection: 'row', gap: 9 }, batteryHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 9 }, batteryShape: { width: 118, height: 36, padding: 4, borderRadius: 7, borderWidth: 3, borderColor: '#68d9ae', marginRight: 14, overflow: 'hidden' }, batteryLow: { borderColor: '#ff777b' }, batteryFill: { height: '100%', backgroundColor: '#50cfa2', borderRadius: 2 }, percent: { color: '#fff', fontSize: 34, fontWeight: '900' }, batteryStatus: { color: '#edf8f4', fontSize: 15, fontWeight: '800' }, lowText: { color: '#ff9194' }, warning: { color: '#ffd36c', fontSize: 14, fontWeight: '700', marginTop: 10 }, location: { color: '#fff', fontSize: 17, lineHeight: 24, fontWeight: '700', marginTop: 13 }, info: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderColor: '#1d3656' }, infoValue: { color: '#f4f8ff', fontWeight: '800', fontSize: 14 }, pipeline: { color: '#adbed1', marginTop: 9, fontSize: 15 }, pipelineSelected: { color: '#72d8b0', marginTop: 1, fontWeight: '800', fontSize: 15 }, storageNumber: { color: '#f4f8ff', fontSize: 22, fontWeight: '900' }, note: { color: '#91a8c4', lineHeight: 19, marginTop: 13, fontSize: 13 }, settingLabel: { color: '#e7effc', marginTop: 19, fontSize: 14, fontWeight: '800' }, periodRow: { flexDirection: 'row', gap: 7, marginTop: 11 }, period: { flex: 1, borderWidth: 1, borderColor: '#3c587a', borderRadius: 9, alignItems: 'center', paddingVertical: 10 }, periodActive: { backgroundColor: '#2e78dc', borderColor: '#5aa0fc' }, periodText: { color: '#e3edfa', fontSize: 12, fontWeight: '800' }, fileList: { marginTop: 13, borderTopWidth: 1, borderColor: '#294563' }, fileRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderColor: '#294563' }, fileInfo: { flex: 1, paddingRight: 8 }, fileName: { color: '#f1f6ff', fontSize: 14, fontWeight: '800' }, fileMeta: { color: '#96abc5', fontSize: 12, marginTop: 4 }, delete: { color: '#ff858a', fontWeight: '800', fontSize: 13 }, empty: { color: '#aebfd3', textAlign: 'center', marginTop: 18 }, tabs: { position: 'absolute', bottom: 0, left: 0, right: 0, flexDirection: 'row', paddingHorizontal: 10, paddingTop: 9, paddingBottom: 20, backgroundColor: '#0e1c30', borderTopWidth: 1, borderColor: '#203957' }, tab: { flex: 1, alignItems: 'center', paddingVertical: 10, borderRadius: 9 }, tabActive: { backgroundColor: '#1d416c' }, tabText: { color: '#9fb3ce', fontSize: 12, fontWeight: '800' }, tabTextActive: { color: '#fff' },
});
