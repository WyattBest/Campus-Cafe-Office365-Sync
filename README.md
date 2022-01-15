#  Campus Cafe to Office 365 Group Sync
Syncs distribution groups from Campus Cafe to Office 365 distribution groups. Requires an SSRS report (one of the few ways to get data out of Campus Cafe) and Azure group GUID for each group to synchronize.

Because the Graph API can't yet modify mail-enabled security groups or distribution groups, EXO V2 PowerShell module is used to add and remove from distribution groups.
