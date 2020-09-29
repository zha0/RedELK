from modules.helpers import *
import traceback

info = {
        'version':0.1,
        'name':'alarm1 module',
        'description':'This check queries for IP\'s that aren\'t listed in any iplist* but do talk to c2* paths on redirectors',
        'type':'redelk_alarm',   # Could also contain redelk_enrich if it was an enrichment module
        'submodule':'alarm1'
    }

class Module():
    def __init__(self):
        #print("class init")
        pass

    def run(self):
        ret = {}
        try:
            report = self.alarm_check1()
            alarmLines = report.get('alarmLines',[])
            # TODO before returning we might have to set an tag on our resultset so we alarm only once. (maybe a tag per alarm?  "ALARMED_%s"%report['fname'] migt do)
            setTags("ALARMED_%s"%info['submodule'],alarmLines)
        except Exception as e:
            stackTrace = traceback.format_exc()
            ret['error'] = stackTrace
            pass
        ret['info'] = info
        ret['hits'] = {}
        ret['hits']['hits'] = alarmLines
        ret['hits']['total'] = len(alarmLines)
        print("[m] finished running module. result:")
        print(ret)
        return(ret)

    def alarm_check1(self):
        ## This check queries for IP's that aren't listed in any iplist* but do talk to c2* paths on redirectors\n
        q = "NOT tags:iplist_* AND redir.backend.name:c2* AND NOT tags:ALARMED_* AND tags:enrich_*"
        i = countQuery(q)
        if i >= 10000: i = 10000
        r = getQuery(q,i)
        report = {}
        report['alarm'] = False
        #if i > 0: report['alarm'] = True #if the query gives 'new ip's we hit on them
        report['fname'] = "alarm_check1"
        report['name'] = "Unkown IP to C2"
        report['description'] = "This check queries for IP's that aren't listed in any iplist* but do talk to c2* paths on redirectors\n"
        report['query'] = q
        UniqueIPs = {}
        if type(r) != type([]) : r = []
        rAlarmed = []
        for ip in r:
            #give enrichment 5 minutes to catch up.
            nowDelayed = datetime.utcnow() - timedelta(minutes=5)
            d = ip['_source']['@timestamp']
            timestamp = datetime.strptime(d, '%Y-%m-%dT%H:%M:%S.%fZ')
            #if timestamp > nowDelayed:
            #  print("item to new %s < %s"%(timestamp,nowDelayed))
            if timestamp < nowDelayed:
                #print("[D] %s < %s"%(timestamp,nowDelayed))
                #print("[D]%s"% ip['_id'])
                rAlarmed.append(ip)
                sip = getValue('_source.source.ip', ip)
                if sip not in UniqueIPs:
                    UniqueIPs[sip] = {}
            UniqueIPs[sip]['http.request.body.content'] = getValue('_source.http.request.body.content', ip)
            UniqueIPs[sip]['source.ip'] = sip
            UniqueIPs[sip]['source.nat.ip'] = getValue('_source.source.nat.ip', ip)
            UniqueIPs[sip]['country_name'] = getValue('_source.source.geo.country_name', ip)
            UniqueIPs[sip]['ISP'] = getValue('_source.source.as.organization.name', ip)
            UniqueIPs[sip]['redir.frontend.name'] = getValue('_source.redir.frontend.name', ip)
            UniqueIPs[sip]['redir.backend.name'] = getValue('_source.redir.backend.name', ip)
            UniqueIPs[sip]['infra.attack_scenario'] = getValue('_source.infra.attack_scenario', ip)
            UniqueIPs[sip]['tags'] = getValue('_source.tags', ip)
            UniqueIPs[sip]['redir.timestamp'] = getValue('_source.redir.timestamp', ip)
            report['alarm'] = True
            print("[A] alarm set in %s"%report['fname'])
            if 'times_seen' in UniqueIPs[sip]: UniqueIPs[sip]['times_seen'] += 1
            else: UniqueIPs[sip]['times_seen'] = 1
        report['results'] = UniqueIPs
        with open("/tmp/ALARMED_alarm_check1.ips","a") as f:
            for ip in UniqueIPs:
                f.write("%s\n"%ip)
        report['alarmLines'] = rAlarmed
        return(report)