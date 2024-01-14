import {type Writable, writable} from "svelte/store";
import {browser} from "$app/environment";
import {ROOT} from "$lib/backend_location";

export interface LoggedInUser {
    username: string;
    token: string;
    id: number;
}

export const userStore: Writable<LoggedInUser | null> = writable(
    null,
    () => {
        if (!browser)
            return;

        const loggedInUser = localStorage.getItem("loggedInUser");
        if (!loggedInUser) return;

        const value = JSON.parse(loggedInUser) satisfies LoggedInUser;
        userStore.set(value);
    }
);

userStore.subscribe((value) => {
    if (!browser)
        return;

    localStorage.setItem("loggedInUser", JSON.stringify(value));
});

export interface Server {
    id: number;
    name: string;
    created_at: string;
    description: string;
    owner: number;
}

export const serverList: Writable<Array<Server> | null> = writable(null);

userStore.subscribe(async function (value) {
    if (!value) {
        serverList.set(null);
        return;
    }

    const res = await fetch(ROOT + "/v1/server", {
        headers: {
            "Authorization": value.token
        }
    });
    if (!res.ok) {
        serverList.set(null);
        return;
    }
    const json = await res.json();
    serverList.set(json);
});

type KnownUsers = Array<Record<number, {username: string}>>;

export const knownUsers: Writable<KnownUsers> = writable([]);
