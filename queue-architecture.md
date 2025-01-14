```mermaid
stateDiagram-v2
    direction LR
    [*] --> WaitingQueue: Join Queue
    
    WaitingQueue --> Draft: Slot Available
    Draft --> Active: Confirm Connection
    Draft --> WaitingQueue: Draft Timeout
    
    Active --> [*]: Session Timeout
    
    state Draft {
        direction LR
        [*] --> DraftTimer
        DraftTimer --> DraftExpired: 5min
    }
    
    state Active {
        direction LR
        [*] --> SessionTimer
        SessionTimer --> SessionExpired: 20min
    }
```