import { Inject, Injectable } from '@angular/core';
import { Http, Headers, URLSearchParams } from '@angular/http';
import { DOCUMENT } from '@angular/platform-browser';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';
import { Subject } from 'rxjs/Subject';

import { WPSResponse } from './wps.service';

export class User {
  id: number;
  username: string;
  openID: string;
  email: string;
  password: string;
  api_key: string;
  type: string;
  local_init: boolean;
  admin: boolean;
}

@Injectable()
export class AuthService {
  admin = new Subject<boolean>();
  logged = this.isLogged();

  admin$ = this.admin.asObservable();
  logged$ = new BehaviorSubject(this.logged);

  constructor(
    @Inject(DOCUMENT) private doc: any,
    private http: Http
  ) { 

    this.user()
      .then(data => {
        let response = data as WPSResponse;

        if (response.status === 'success') {
          let userObj = response.data as User;

          this.admin.next(userObj.admin);
        }
      });
  }

  isLogged(): boolean {
    let expires = localStorage.getItem('wps_expires');

    if (expires != null) {
      let expiresDate = new Date(expires);

      if (expiresDate.getTime() > Date.now()) {
          return true
      }
    }

    return false;
  }

  setExpires(expires: string) {
    localStorage.setItem('wps_expires', expires);

    this.logged$.next(true);
  }

  getCookie(name: string): string {
    let cookieValue: string = null;

    if (this.doc.cookie && this.doc.cookie !== '') {
      let cookies: string[] = this.doc.cookie.split(';');

      for (let cookie of cookies) {
        if (cookie.trim().substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.trim().substring(name.length + 1));

          break;
        }
      }
    }

    return cookieValue;
  }

  userToUrlEncoded(user: User): string {
    let params: string = '';

    for (let k in user) {
      params += `${k.toLowerCase()}=${user[k]}&`;
    }

    return params;
  }

  resetPassword(data: any) {
    let params = new URLSearchParams();

    params.set('username', data.username);
    params.set('token', data.token);
    params.set('password', data.password);

    return this.http.get('auth/reset', {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      }),
      params: params
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  forgotPassword(username: string): Promise<WPSResponse> {
    let params = new URLSearchParams();

    params.set('username', username);

    return this.http.get('auth/forgot/password', {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      }),
      params: params
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  forgotUsername(email: string): Promise<WPSResponse> {
    let params = new URLSearchParams();

    params.set('email', email);

    return this.http.get('auth/forgot/username', {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      }),
      params: params
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  create(user: User): Promise<WPSResponse> {
    return this.http.post('auth/create/', this.userToUrlEncoded(user), {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  update(user: User): Promise<WPSResponse> {
    return this.http.post('auth/update/', this.userToUrlEncoded(user), {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  login(user: User): Promise<WPSResponse> {
    return this.http.post('auth/login/', this.userToUrlEncoded(user), {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => this.handleLoginResponse(response.json() as WPSResponse))
      .catch(this.handleError);
  }

  loginOpenID(openidURL: string): Promise<WPSResponse> {
    return this.http.post('auth/login/openid/', `openid_url=${openidURL}`, {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  logout(): Promise<WPSResponse> {
    return this.http.get('auth/logout/', {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => this.handleLogoutResponse(response.json() as WPSResponse))
      .catch(this.handleError);
  }

  user(): Promise<any> {
    return this.http.get('auth/user/', {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  regenerateKey(user: User): Promise<WPSResponse> {
    return this.http.get(`auth/user/regenerate/`, {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  oauth2(openid: string): Promise<WPSResponse> {
    return this.http.post('auth/login/oauth2/', `openid=${openid}`, {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  myproxyclient(user: User): Promise<WPSResponse> {
    return this.http.post('auth/login/mpc/', `username=${user.username}&password=${user.password}`, {
      headers: new Headers({
        'X-CSRFToken': this.getCookie('csrftoken'),
        'Content-Type': 'application/x-www-form-urlencoded'
      })
    })
      .toPromise()
      .then(response => response.json() as WPSResponse)
      .catch(this.handleError);
  }

  private handleLoginResponse(response: WPSResponse): WPSResponse {
    if (response.status === 'success') {
      localStorage.setItem('wps_expires', response.data.expires);

      this.logged$.next(true);
    } else {
      this.handleLogoutResponse(response);
    }

    return response
  }

  private handleLogoutResponse(response: WPSResponse): WPSResponse {
    localStorage.removeItem('wps_expires');

    this.logged$.next(false);

    return response;
  }

  private handleError(error: any): Promise<any> {
    return Promise.reject(error.message || error);
  }
}
